#!/usr/bin/env python3
"""
Nova AI — GUI Flow Replicator (credential-free build)
=====================================================
Replicates only the two captured flows, using credentials the user
supplies themselves (no hardcoded keys, tokens, or device IDs):

  ABRIR A APLICAÇÃO
    1. GET  /api/android/userstatus
    2. POST /api/v3/users/{userId}

  INICIAR CONVERSA
    3. POST /api/chat/title   -> conversation title
    4. POST /api/chat         -> message + SSE response

Required (per captured traffic, entered by the user at runtime):
  - User_ID : device-unique userId used in the /users/{userId} URL
  - X_TOKEN : a *real* captured Firebase token (1-hour validity)

Headers used for replication (from the analysis):
  X_TOKEN, X_PLATFORM=android, X_PR=false  (+ X_USER_ID / X_VERSION for routing)

Optional:
  - modelMap : loaded from a user-provided JSON file if available
               (captured separately; not bundled with this script)

Requires:
    pip install customtkinter requests curl_cffi
"""

import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk
import threading
import requests
import random
import string
import json

try:
    from curl_cffi import requests as cf_requests
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False


# ─────────────────────────────────────────────
# CONFIG (no secrets — only the public base URL + non-sensitive flags)
# ─────────────────────────────────────────────
NOVA_API_BASE = "https://api.novaapp.ai"

CF_IMPERSONATE_PROFILES = ["chrome120", "chrome116", "chrome110", "safari17_0"]

# Model picker. Only the numeric model selectors observed in the request
# bodies — no names, no secret values. If your captured traffic also
# requires a modelMap, load it from a JSON file at runtime.
MODEL_OPTIONS = {str(n): n for n in
                 [0, 2, 10, 15, 16, 19, 23, 29, 49]}


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def generate_chat_id():
    """Firestore-style 20-char alphanumeric ID, matching X_CHAT_ID format."""
    chars = string.ascii_letters + string.digits
    return "".join(random.choices(chars, k=20))


def nova_headers(x_token, user_id, extra=None):
    """
    Minimal Nova headers. Per the captured analysis the replication only
    requires X_TOKEN, X_PLATFORM and X_PR; X_USER_ID / X_VERSION are kept
    for request routing. Nothing here is hardcoded — all identity values
    come from what the user entered.
    """
    h = {
        "Content-Type":    "application/json; charset=UTF-8",
        "Accept-Encoding": "gzip",
        "Connection":      "Keep-Alive",
        "X_PLATFORM":      "android",
        "X_PR":            "false",
        "X_TOKEN":         x_token,
        "X_USER_ID":       user_id,
        "X_VERSION":       "3",
    }
    if extra:
        h.update(extra)
    return h


# ─────────────────────────────────────────────
# MAIN APP
# ─────────────────────────────────────────────

class NovaReplicatorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # State — all credential state starts empty and is filled by the user
        self.x_token              = ""
        self.user_id              = ""
        self.model_map            = []      # optional, loaded from file
        self.session_ready        = False

        self.cf_cookies           = {}
        self.cf_profile           = CF_IMPERSONATE_PROFILES[0]
        self.conversation_history = []
        self.current_chat_id      = None
        self.conversation_model   = None
        self.conversation_title   = None

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.title("Nova AI — Flow Replicator")
        self.geometry("1100x800")
        self.minsize(900, 680)
        self.configure(fg_color="#0f1117")

        self._build_ui()

    # ── UI ───────────────────────────────────────────────

    def _build_ui(self):
        top = ctk.CTkFrame(self, fg_color="#161b27", height=52, corner_radius=0)
        top.pack(fill="x", side="top")
        top.pack_propagate(False)
        ctk.CTkLabel(top, text="⬡  Nova AI  —  Flow Replicator",
                     font=("Consolas", 13, "bold"),
                     text_color="#58a6ff").pack(side="left", padx=18, pady=14)
        self.status_badge = ctk.CTkLabel(top, text="● NO CREDENTIALS",
                                         font=("Consolas", 11),
                                         text_color="#f85149")
        self.status_badge.pack(side="right", padx=18)

        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=12, pady=(8, 4))

        left = ctk.CTkFrame(main, fg_color="#161b27", corner_radius=10, width=380)
        left.pack(side="left", fill="y", padx=(0, 6))
        left.pack_propagate(False)
        self._build_session_panel(left)

        right = ctk.CTkFrame(main, fg_color="transparent")
        right.pack(side="left", fill="both", expand=True)
        self._build_chat_panel(right)
        self._build_log_panel(right)

    def _build_session_panel(self, parent):
        ctk.CTkLabel(parent, text="CREDENTIALS (user-supplied)",
                     font=("Consolas", 11, "bold"),
                     text_color="#8b949e").pack(anchor="w", padx=16, pady=(14, 2))

        # ── Credential entry ──
        s0 = self._section(parent, "Captured Session")
        ctk.CTkLabel(s0, text="Paste your own captured values.\n"
                              "X_TOKEN is only valid ~1 hour.",
                     font=("Consolas", 10), text_color="#8b949e",
                     justify="left").pack(anchor="w", padx=4, pady=(2, 6))

        ctk.CTkLabel(s0, text="User_ID  (device userId):",
                     font=("Consolas", 10), text_color="#8b949e",
                     anchor="w").pack(anchor="w", padx=4)
        self.entry_user_id = ctk.CTkEntry(s0, font=("Consolas", 11),
                                          placeholder_text="e.g. 32-hex device id",
                                          height=32)
        self.entry_user_id.pack(fill="x", padx=4, pady=(2, 8))

        ctk.CTkLabel(s0, text="X_TOKEN  (captured, ~1h TTL):",
                     font=("Consolas", 10), text_color="#8b949e",
                     anchor="w").pack(anchor="w", padx=4)
        self.entry_token = ctk.CTkEntry(s0, font=("Consolas", 11),
                                        placeholder_text="paste captured token",
                                        height=32, show="•")
        self.entry_token.pack(fill="x", padx=4, pady=(2, 4))
        self.chk_show_token = ctk.CTkCheckBox(s0, text="show token",
                                              font=("Consolas", 10),
                                              command=self._toggle_token_visibility)
        self.chk_show_token.pack(anchor="w", padx=4, pady=(0, 8))

        self.btn_apply = ctk.CTkButton(s0, text="Apply Credentials",
                                       font=("Consolas", 12, "bold"),
                                       fg_color="#1f6feb", hover_color="#388bfd",
                                       height=34, command=self._on_apply_creds)
        self.btn_apply.pack(fill="x", padx=4)
        self.lbl_creds = ctk.CTkLabel(s0, text="", font=("Consolas", 10),
                                      text_color="#8b949e")
        self.lbl_creds.pack(anchor="w", padx=4, pady=(3, 0))

        # ── Optional modelMap ──
        sm = self._section(parent, "modelMap (optional)")
        ctk.CTkLabel(sm, text="Load a captured modelMap JSON if your\n"
                              "traffic requires it. Not bundled here.",
                     font=("Consolas", 10), text_color="#8b949e",
                     justify="left").pack(anchor="w", padx=4, pady=(2, 6))
        self.btn_load_map = ctk.CTkButton(sm, text="Load modelMap JSON…",
                                          font=("Consolas", 11),
                                          fg_color="#21262d", hover_color="#30363d",
                                          border_color="#30363d", border_width=1,
                                          height=30, command=self._on_load_modelmap)
        self.btn_load_map.pack(fill="x", padx=4)
        self.lbl_map = ctk.CTkLabel(sm, text="No modelMap loaded",
                                    font=("Consolas", 10), text_color="#8b949e")
        self.lbl_map.pack(anchor="w", padx=4, pady=(3, 0))

        # ── Open app flow ──
        s1 = self._section(parent, "Abrir a aplicação")
        ctk.CTkLabel(s1, text="GET /api/android/userstatus\n"
                              "POST /api/v3/users/{userId}",
                     font=("Consolas", 10), text_color="#8b949e",
                     justify="left").pack(anchor="w", padx=4, pady=(2, 6))
        self.btn_open_app = ctk.CTkButton(s1, text="Run Open-App Flow",
                                          font=("Consolas", 12, "bold"),
                                          fg_color="#1f6feb", hover_color="#388bfd",
                                          height=34, command=self._on_open_app)
        self.btn_open_app.pack(fill="x", padx=4)
        self.lbl_open = ctk.CTkLabel(s1, text="", font=("Consolas", 10),
                                     text_color="#8b949e")
        self.lbl_open.pack(anchor="w", padx=4, pady=(3, 0))

        # ── Session info ──
        s2 = self._section(parent, "Session Info")
        labels = ["Nova User ID", "User Status", "Premium"]
        self.info_labels = {}
        for lbl in labels:
            row = ctk.CTkFrame(s2, fg_color="transparent")
            row.pack(fill="x", padx=4, pady=1)
            ctk.CTkLabel(row, text=f"{lbl}:", font=("Consolas", 10),
                         text_color="#8b949e", width=100, anchor="w").pack(side="left")
            val = ctk.CTkLabel(row, text="—", font=("Consolas", 10),
                               text_color="#e6edf3", anchor="w")
            val.pack(side="left", fill="x", expand=True)
            self.info_labels[lbl] = val

    def _build_chat_panel(self, parent):
        chat_frame = ctk.CTkFrame(parent, fg_color="#161b27", corner_radius=10)
        chat_frame.pack(fill="both", expand=True, pady=(0, 6))

        hdr = ctk.CTkFrame(chat_frame, fg_color="transparent")
        hdr.pack(fill="x", padx=14, pady=(10, 4))
        ctk.CTkLabel(hdr, text="INICIAR CONVERSA", font=("Consolas", 11, "bold"),
                     text_color="#8b949e").pack(side="left")

        ctk.CTkLabel(hdr, text="Model:", font=("Consolas", 11),
                     text_color="#8b949e").pack(side="left", padx=(12, 4))
        self.model_var = ctk.StringVar(value="0")
        self.model_menu = ctk.CTkOptionMenu(hdr, variable=self.model_var,
                                            values=list(MODEL_OPTIONS.keys()),
                                            font=("Consolas", 11),
                                            fg_color="#21262d",
                                            button_color="#30363d",
                                            width=180)
        self.model_menu.pack(side="left")

        self.lbl_title = ctk.CTkLabel(hdr, text="",
                                      font=("Consolas", 10, "italic"),
                                      text_color="#8b949e")
        self.lbl_title.pack(side="left", padx=(10, 0))

        self.btn_new_chat = ctk.CTkButton(hdr, text="New Chat",
                                          font=("Consolas", 11),
                                          fg_color="#21262d", hover_color="#30363d",
                                          border_color="#30363d", border_width=1,
                                          width=80, height=28,
                                          command=self._new_conversation)
        self.btn_new_chat.pack(side="right", padx=(0, 4))

        self.btn_clear = ctk.CTkButton(hdr, text="Clear",
                                       font=("Consolas", 11),
                                       fg_color="#21262d", hover_color="#30363d",
                                       border_color="#30363d", border_width=1,
                                       width=60, height=28,
                                       command=self._clear_chat)
        self.btn_clear.pack(side="right")

        self.chat_display = ctk.CTkTextbox(chat_frame,
                                           font=("Consolas", 12),
                                           fg_color="#0d1117",
                                           text_color="#e6edf3",
                                           wrap="word", state="disabled")
        self.chat_display.pack(fill="both", expand=True, padx=14, pady=(0, 8))
        self.chat_display.tag_config("user",   foreground="#58a6ff")
        self.chat_display.tag_config("bot",    foreground="#e6edf3")
        self.chat_display.tag_config("system", foreground="#8b949e")
        self.chat_display.tag_config("error",  foreground="#f85149")
        self.chat_display.tag_config("title",  foreground="#d2a8ff")

        inp = ctk.CTkFrame(chat_frame, fg_color="transparent")
        inp.pack(fill="x", padx=14, pady=(0, 12))
        self.msg_entry = ctk.CTkEntry(inp, placeholder_text="Type a message…",
                                      font=("Consolas", 12), height=38)
        self.msg_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.msg_entry.bind("<Return>", lambda e: self._on_send_message())
        self.btn_send_msg = ctk.CTkButton(inp, text="Send ▶",
                                          font=("Consolas", 12, "bold"),
                                          fg_color="#1f6feb", hover_color="#388bfd",
                                          width=90, height=38,
                                          command=self._on_send_message)
        self.btn_send_msg.pack(side="left")

    def _build_log_panel(self, parent):
        log_frame = ctk.CTkFrame(parent, fg_color="#161b27",
                                 corner_radius=10, height=130)
        log_frame.pack(fill="x")
        log_frame.pack_propagate(False)
        ctk.CTkLabel(log_frame, text="REQUEST LOG",
                     font=("Consolas", 10, "bold"),
                     text_color="#8b949e").pack(anchor="w", padx=14, pady=(8, 2))
        self.log_box = ctk.CTkTextbox(log_frame, font=("Consolas", 10),
                                      fg_color="#0d1117", text_color="#8b949e",
                                      state="disabled", height=88)
        self.log_box.pack(fill="both", expand=True, padx=14, pady=(0, 8))

    def _section(self, parent, title):
        outer = ctk.CTkFrame(parent, fg_color="#0d1117", corner_radius=8,
                             border_color="#21262d", border_width=1)
        outer.pack(fill="x", padx=12, pady=5)
        ctk.CTkLabel(outer, text=title, font=("Consolas", 10, "bold"),
                     text_color="#58a6ff").pack(anchor="w", padx=10, pady=(8, 2))
        inner = ctk.CTkFrame(outer, fg_color="transparent")
        inner.pack(fill="x", padx=6, pady=(0, 8))
        return inner

    # ── Thread-safe helpers ──────────────────────────────

    def _ui(self, fn, *args, **kwargs):
        try:
            self.after(0, lambda: fn(*args, **kwargs))
        except Exception:
            pass

    def _log(self, msg, level="info"):
        prefix = {"info": "  ", "ok": "✓ ", "err": "✗ ", "req": "→ "}
        line = f"{prefix.get(level,'  ')}{msg}\n"
        def _do():
            try:
                self.log_box.configure(state="normal")
                self.log_box.insert("end", line)
                self.log_box.see("end")
                self.log_box.configure(state="disabled")
            except Exception:
                pass
        self._ui(_do)

    def _chat_append(self, text, tag="system"):
        def _do():
            try:
                self.chat_display.configure(state="normal")
                self.chat_display.insert("end", text, tag)
                self.chat_display.see("end")
                self.chat_display.configure(state="disabled")
            except Exception:
                pass
        self._ui(_do)

    def _clear_chat(self):
        def _do():
            self.chat_display.configure(state="normal")
            self.chat_display.delete("1.0", "end")
            self.chat_display.configure(state="disabled")
        self._ui(_do)

    def _set_info(self, key, val):
        if key in self.info_labels:
            display = val if len(str(val)) < 44 else str(val)[:41] + "…"
            self._ui(self.info_labels[key].configure, text=display)

    def _run_thread(self, fn):
        threading.Thread(target=fn, daemon=True).start()

    def _toggle_token_visibility(self):
        self.entry_token.configure(show="" if self.chk_show_token.get() else "•")

    def _new_conversation(self):
        self.conversation_history = []
        self.current_chat_id      = None
        self.conversation_model   = None
        self.conversation_title   = None
        self._clear_chat()
        self._ui(self.lbl_title.configure, text="")
        self._log("New conversation started", "ok")
        self._chat_append("[System] New conversation. Title set on first message.\n",
                          "system")

    # ── Credentials ──────────────────────────────────────

    def _on_apply_creds(self):
        user_id = self.entry_user_id.get().strip()
        token   = self.entry_token.get().strip()
        if not user_id or not token:
            messagebox.showwarning("Credentials",
                                   "Both User_ID and X_TOKEN are required.")
            return
        self.user_id       = user_id
        self.x_token       = token
        self.session_ready = True
        self._set_info("Nova User ID", self.user_id)
        self._ui(self.status_badge.configure,
                 text="● CREDENTIALS SET", text_color="#3fb950")
        self._ui(self.lbl_creds.configure,
                 text="✓ Credentials applied", text_color="#3fb950")
        self._log("Credentials applied (user-supplied)", "ok")

    def _on_load_modelmap(self):
        path = filedialog.askopenfilename(
            title="Select captured modelMap JSON",
            filetypes=[("JSON", "*.json"), ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # accept either a raw list or {"model": [...]}
            self.model_map = data.get("model", data) if isinstance(data, dict) else data
            n = len(self.model_map) if isinstance(self.model_map, list) else 0
            self._ui(self.lbl_map.configure,
                     text=f"✓ Loaded {n} entries", text_color="#3fb950")
            self._log(f"modelMap loaded: {n} entries", "ok")
        except Exception as e:
            self._ui(self.lbl_map.configure,
                     text=f"✗ {e}", text_color="#f85149")
            self._log(f"modelMap load error: {e}", "err")

    def _require_session(self):
        if not self.session_ready:
            messagebox.showwarning("Credentials",
                                   "Apply your User_ID and X_TOKEN first.")
            return False
        return True

    # ── HTTP helpers (curl_cffi with optional CF impersonation) ──

    def _http_get(self, url):
        if HAS_CURL_CFFI:
            return cf_requests.get(url,
                                   headers=nova_headers(self.x_token, self.user_id),
                                   cookies=self.cf_cookies,
                                   impersonate=self.cf_profile, timeout=10)
        return requests.get(url,
                            headers=nova_headers(self.x_token, self.user_id),
                            timeout=10)

    def _http_post(self, url, payload, extra_headers=None, stream=False):
        headers = nova_headers(self.x_token, self.user_id, extra_headers)
        if HAS_CURL_CFFI:
            return cf_requests.post(url, headers=headers, json=payload,
                                    cookies=self.cf_cookies,
                                    impersonate=self.cf_profile,
                                    stream=stream, timeout=30)
        return requests.post(url, headers=headers, json=payload,
                             stream=stream, timeout=30)

    # ── ABRIR A APLICAÇÃO ────────────────────────────────

    def _on_open_app(self):
        if not self._require_session():
            return
        self._run_thread(self._open_app_flow)

    def _open_app_flow(self):
        self._user_status()
        self._setup_user()

    def _user_status(self):
        """GET /api/android/userstatus -> {data: "false", timestamp: ...}."""
        url = f"{NOVA_API_BASE}/api/android/userstatus"
        self._log("GET /api/android/userstatus", "req")
        try:
            resp = self._http_get(url)
            self._log(f"userstatus: {resp.status_code}",
                      "ok" if resp.status_code == 200 else "err")
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    self._set_info("User Status", str(data.get("data", "?")))
                    self._log(f"  body: {json.dumps(data)[:200]}", "info")
                except Exception:
                    self._log(f"  raw: {resp.text[:200]}", "info")
        except Exception as e:
            self._log(f"userstatus exception: {e}", "err")

    def _setup_user(self):
        """POST /api/v3/users/{userId} -> subscription + credit info."""
        url = f"{NOVA_API_BASE}/api/v3/users/{self.user_id}"
        # modelMap is optional; only included if the user loaded one.
        payload = {"fcmToken": "none"}
        if self.model_map:
            payload["model"] = self.model_map
        self._log(f"POST /api/v3/users/{self.user_id[:16]}…", "req")
        try:
            resp = self._http_post(url, payload)
            self._log(f"users: {resp.status_code}",
                      "ok" if resp.status_code in (200, 201) else "err")
            if resp.status_code in (200, 201):
                data = resp.json()
                inner = data.get("data") or data
                self._set_info("Premium", str(inner.get("isPremium", "?")))
                self._log(f"  body: {json.dumps(data)[:240]}", "info")
                self._ui(self.lbl_open.configure,
                         text="✓ Open-app flow OK", text_color="#3fb950")
            else:
                self._log(f"users body: {resp.text[:200]}", "err")
                self._ui(self.lbl_open.configure,
                         text=f"✗ {resp.status_code}", text_color="#f85149")
        except Exception as e:
            self._log(f"users exception: {e}", "err")

    # ── INICIAR CONVERSA ─────────────────────────────────

    def _on_send_message(self):
        if not self._require_session():
            return
        msg = self.msg_entry.get().strip()
        if not msg:
            return
        model_id = MODEL_OPTIONS[self.model_var.get()]

        if (self.conversation_history and
                self.conversation_model is not None and
                self.conversation_model != model_id):
            if messagebox.askyesno("Model changed",
                f"Conversation started with model {self.conversation_model}, "
                f"now {model_id} is selected.\n\nStart a new conversation?"):
                self._new_conversation()

        self.msg_entry.delete(0, "end")
        self._chat_append(f"\n[You]  {msg}\n", "user")
        self._chat_append(f"[Nova] ", "system")
        self._ui(self.btn_send_msg.configure, state="disabled", text="…")
        self._run_thread(lambda: self._chat_flow(msg, model_id))

    def _chat_flow(self, message, model_id):
        try:
            if self.current_chat_id is None:
                self._chat_title(message, model_id)
                self.current_chat_id    = generate_chat_id()
                self.conversation_model = model_id
            self._send_chat(message, model_id)
        except Exception as e:
            self._chat_append(f"\n[Exception] {e}\n", "error")
            self._log(f"Chat flow exception: {e}", "err")
        finally:
            self._ui(self.btn_send_msg.configure, state="normal", text="Send ▶")

    def _chat_title(self, message, model_id):
        """POST /api/chat/title — generates a conversation title."""
        url = f"{NOVA_API_BASE}/api/chat/title"
        payload = {"content": message, "model": model_id}
        self._log(f"POST /api/chat/title  model={model_id}", "req")
        try:
            resp = self._http_post(url, payload)
            self._log(f"title: {resp.status_code}",
                      "ok" if resp.status_code == 200 else "err")
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    self._log(f"  body: {json.dumps(data)[:200]}", "info")
                    inner = data.get("data") or data
                    title = (inner.get("title") or inner.get("name") or
                             data.get("title") or "")
                    if title:
                        self.conversation_title = title
                        self._ui(self.lbl_title.configure, text=f"« {title} »")
                        self._chat_append(f"[Title]  {title}\n", "title")
                except Exception:
                    self._log(f"  raw: {resp.text[:200]}", "info")
            else:
                self._log(f"title body: {resp.text[:200]}", "err")
        except Exception as e:
            self._log(f"title exception: {e}", "err")

    def _send_chat(self, message, model_id):
        """POST /api/chat — send message with SSE streaming response."""
        url = f"{NOVA_API_BASE}/api/chat"
        cumulative_tokens = sum(m.get("a", 0) for m in self.conversation_history)
        messages = list(self.conversation_history) + [
            {"content": message, "role": "user"}
        ]
        headers_extra = {
            "Accept":            "text/event-stream",
            "Content-Type":      "application/json; charset=utf-8",
            "X_CHAT_ID":         self.current_chat_id,
            "X_MODEL":           str(model_id),
            "X_STREAM":          "true",
            "X_SEARCH":          "false",
            "X_TOKEN_COUNT":     str(cumulative_tokens),
        }
        payload = {"messages": messages}
        if self.model_map:
            payload["modelMap"] = self.model_map

        self._log(f"POST /api/chat  model={model_id}  chat_id={self.current_chat_id}",
                  "req")

        for profile in CF_IMPERSONATE_PROFILES:
            try:
                if HAS_CURL_CFFI:
                    resp = cf_requests.post(
                        url,
                        headers=nova_headers(self.x_token, self.user_id, headers_extra),
                        json=payload, cookies=self.cf_cookies, stream=True,
                        impersonate=profile, timeout=30)
                else:
                    resp = requests.post(url,
                        headers=nova_headers(self.x_token, self.user_id, headers_extra),
                        json=payload, stream=True, timeout=30)

                self._log(f"chat: {resp.status_code}  profile={profile}",
                          "ok" if resp.status_code == 200 else "err")

                if resp.status_code == 403 and "Just a moment" in resp.text:
                    self._log(f"CF blocked {profile}, trying next", "err")
                    continue

                if resp.cookies:
                    self.cf_cookies.update(dict(resp.cookies))
                    self.cf_profile = profile

                if resp.status_code == 200:
                    assistant_text = self._parse_sse_stream(resp)
                    self.conversation_history.append({
                        "a": len(message), "content": message, "role": "user"
                    })
                    if assistant_text:
                        self.conversation_history.append({
                            "a": len(assistant_text),
                            "content": assistant_text, "role": "assistant"
                        })
                    return
                else:
                    err_code = resp.headers.get("custom-error-code", "n/a")
                    body = resp.text[:500] if hasattr(resp, "text") else ""
                    self._log(f"  custom-error-code: {err_code}", "err")
                    self._log(f"  body: {body}", "err")
                    self._chat_append(
                        f"\n[Error {resp.status_code}  code={err_code}]\n{body}\n",
                        "error")
                    return
            except Exception as e:
                self._log(f"Exception profile={profile}: {e}", "err")
                continue

        self._chat_append("\n[Error] All TLS profiles blocked\n", "error")

    def _parse_sse_stream(self, resp):
        """Parse SSE; return concatenated assistant text."""
        full_text = []
        try:
            for line in resp.iter_lines():
                if not line:
                    continue
                decoded = line if isinstance(line, str) else line.decode("utf-8", errors="replace")
                if decoded.startswith("data:"):
                    data_str = decoded[5:].strip()
                    if not data_str or data_str == "[DONE]":
                        continue
                    try:
                        chunk = json.loads(data_str)
                        content = (
                            chunk.get("content") or chunk.get("text") or
                            chunk.get("message") or
                            (chunk.get("delta", {}) or {}).get("content") or
                            (chunk.get("choices", [{}])[0].get("delta", {}) or {}).get("content") or
                            (chunk.get("choices", [{}])[0].get("message", {}) or {}).get("content") or
                            ""
                        )
                        if content:
                            self._chat_append(content, "bot")
                            full_text.append(content)
                    except json.JSONDecodeError:
                        pass
        except Exception as e:
            self._log(f"Stream exception: {e}", "err")
        finally:
            self._chat_append("\n", "system")
        return "".join(full_text)


# ─────────────────────────────────────────────
if __name__ == "__main__":
    if not HAS_CURL_CFFI:
        print("WARNING: curl_cffi not installed; TLS impersonation disabled.")
        print("Run: pip install curl_cffi")
    app = NovaReplicatorApp()
    app.mainloop()