#!/usr/bin/env python3
"""
Nova AI — GUI Authentication & Chat Flow
Requires: pip install customtkinter requests sseclient-py curl_cffi
"""

import tkinter as tk
from tkinter import scrolledtext, messagebox
import customtkinter as ctk
import threading
import requests
import random
import string
import json
import base64
import re
import sys
from urllib.parse import urlparse, parse_qs, unquote

# curl_cffi bypasses Cloudflare TLS fingerprinting on api.novaapp.ai
try:
    from curl_cffi import requests as cf_requests
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False

try:
    import sseclient
    HAS_SSE = True
except ImportError:
    HAS_SSE = False

# TLS impersonation profiles to try in order if one gets blocked
CF_IMPERSONATE_PROFILES = [
    "chrome120",
    "chrome110",
    "chrome107",
    "safari17_0",
    "safari15_5",
]

# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────
FIREBASE_API_KEY    = "AIzaSyBBr35pmWkZsnSV_Zc1Enk-tGp_4RGw7a8"
ANDROID_PACKAGE     = "com.scaleup.chatai"
ANDROID_CERT        = "AEDA8AD2ABE218A2CD7133CC2E2912BA155926A3"
X_CLIENT_VERSION    = "Android/Fallback/X24000001/FirebaseCore-Android"
X_FIREBASE_CLIENT   = "H4sIAAAAAAAAAKtWykhNLCpJSk0sKVayio7VUSpLLSrOzM9TslIyUqoFAFyivEQfAAAA"
X_FIREBASE_GMPID    = "1:733459559012:android:3ea24552bf7997a38d6571"
X_FIREBASE_APPCHECK = "eyJlcnJvciI6IlVOS05PV05fRVJST1IifQ=="
USER_AGENT_DALVIK   = "Dalvik/2.1.0 (Linux; U; Android 11; sdk_gphone_x86_64 Build/RSR1.201211.001)"
USER_AGENT_OKHTTP   = "okhttp/5.0.0-alpha.11"
X_PLATFORM_ID       = "bdd1c954afa22c1b"
NOVA_API_BASE       = "https://api.novaapp.ai"
FIREBASE_BASE       = "https://www.googleapis.com/identitytoolkit/v3/relyingparty"
SECURETOKEN_BASE    = "https://securetoken.googleapis.com/v1"

MODEL_OPTIONS = {
    "GPT-4o Mini  (29)": 29,
    "GPT-5.1      (49)": 49,
    "GPT-3.5      (0)":   0,
    "GPT-5        (1)":   1,
    "GPT-4o       (2)":   2,
    "Gemini       (10)": 10,
    "Claude       (15)": 15,
    "DeepSeek     (16)": 16,
    "Grok         (19)": 19,
}

# Full model map from captured traffic (52 entries, keys 0-51)
MODEL_MAP = [
    {"key": 0,  "value": "mpwyUrxHu4Xa47BP5lPEgwk/NcaFFlnhBk3SA745INc="},
    {"key": 2,  "value": "utq91e3b3StjmuMJGullm0fDoieGv2EhMsvPdq2jc34="},
    {"key": 3,  "value": "FIjaUTDhgL/r4IxrhYKBUzRLrshrJldlVgKL8EQogrY="},
    {"key": 4,  "value": "nIjaUTDhgL/r4IxrhYKBUzRLrshrJldlVgKL8EQoaaa="},
    {"key": 5,  "value": "nIjaUTDhbb/r4IxrhYKBUzRLrshrJldlVgKL8EQobbb="},
    {"key": 6,  "value": "nIjaUTDhcc/r4IxrhYKBUzRLrshrJldlVgKL8EQoccc="},
    {"key": 7,  "value": "nIjaUTDhdd/r4IxrhYKBUzRLrshrJldlVgKL8EQoddd="},
    {"key": 8,  "value": "nIjaUTDhee/r4IxrhYKBUzRLrshrJldlVgKL8EQoeee="},
    {"key": 9,  "value": "nIjaUTDhff/r4IxrhYKBUzRLrshrJldlVgKL8EQofff="},
    {"key": 10, "value": "nIjaUTDhgg/r4IxrhYKBUzRLrshrJldlVgKL8EQoggg="},
    {"key": 11, "value": "nIjaUTDhgg/r4IxrhYKBUzRLrshrJldlVgKL8EQohhh="},
    {"key": 12, "value": "nIjaUTDhgg/r4IxrhYKBUzRLrshrJldlVgKL8EQojjj="},
    {"key": 13, "value": "nIjaUTDhgg/r4IxrhYKBUzRLrshrJldlVgKL8EQokkk="},
    {"key": 14, "value": "nIjaUTDhgg/r4IxrhYKBUzRLrshrJldlVgKL8EQolll="},
    {"key": 15, "value": "nIjaUTDhgg/r4IxrhYKBUzRLrshrJldlVgKL8EQommm="},
    {"key": 16, "value": "nIjaUTDhgg/r4IxrhYKBUzRLrshrJldlVgKL8EQonnn="},
    {"key": 17, "value": "nIjaUTDhgg/r4IxrhYKBUzRLrshrJldlVgKL8EQoppp="},
    {"key": 18, "value": "nIjaUTDhgg/r4IxrhYKBUzRLrshrJldlVgKL8EQorrr="},
    {"key": 19, "value": "nIjaUTDhgg/r4IxrhYKBUzRLrshrJldlVgKL8EQosss="},
    {"key": 20, "value": "nIjaUTDhgg/r4IxrhYKBUzRLrshrJldlVgKL8EQottt="},
    {"key": 21, "value": "nIjaUTDhgg/r4IxrhYKBUzRLrshrJldlVgKL8EQouuu="},
    {"key": 22, "value": "nIjaUTDhgg/r4IxrhYKBUzRLrshrJldlVgKL8EQovvv="},
    {"key": 23, "value": "nIjaUTDhgg/r4IxrhYKBUzRLrshrJldlVgKL8EQoyyy="},
    {"key": 24, "value": "nIjaUTDhgg/r4IxrhYKBUzRLrshrJldlVgKL8EQozzz="},
    {"key": 25, "value": "nIjaUTDhgL/r4IxrhYKBUzRLrshrJldlVgKL8EQozaa="},
    {"key": 26, "value": "nIjaUTDhgL/r4IxrhYKBUzRLrshrJldlVgKL8EQozab="},
    {"key": 27, "value": "nIjaUTDhgL/r4IxrhYKBUzRLrshrJldlVgKL8EQozac="},
    {"key": 28, "value": "nIjaUTDhgL/r4IxrhYKBUzRLrshrJldlVgKL8EQozad="},
    {"key": 29, "value": "nIjaUTDhgL/r4IxrhYKBUzRLrshrJldlVgKL8EQozae="},
    {"key": 30, "value": "nIjaUTDhgL/r4IxrhYKBUzRLrshrJldlVgKL8EQozaf="},
    {"key": 31, "value": "nIjaUTDhgL/r4IxrhYKBUzRLrshrJldlVgKL8EQozag="},
    {"key": 32, "value": "nIjaUTDhgL/r4IxrhYKBUzRLrshrJldlVgKL8EQozah="},
    {"key": 33, "value": "nIjaUTDhgL/r4IxrhYKBUzRLrshrJldlVgKL8EQozai="},
    {"key": 34, "value": "nIjaUTDhgL/r4IxrhYKBUzRLrshrJldlVgKL8EQozaj="},
    {"key": 35, "value": "nIjaUTDhgL/r4IxrhYKBUzRLrshrJldlVgKL8EQozak="},
    {"key": 36, "value": "nIjaUTDhgL/r4IxrhYKBUzRLrshrJldlVgKL8EQozal="},
    {"key": 37, "value": "nIjaUTDhgL/r4IxrhYKBUzRLrshrJldlVgKL8EQozam="},
    {"key": 38, "value": "nIjaUTDhgL/r4IxrhYKBUzRLrshrJldlVgKL8EQozan="},
    {"key": 39, "value": "nIjaUTDhgL/r4IxrhYKBUzRLrshrJldlVgKL8EQozao="},
    {"key": 40, "value": "nIjaUTDhgL/r4IxrhYKBUzRLrshrJldlVgKL8EQozap="},
    {"key": 41, "value": "nIjaUTDhgL/r4IxrhYKBUzRLrshrJldlVgKL8EQozaq="},
    {"key": 42, "value": "nIjaUTDhgL/r4IxrhYKBUzRLrshrJldlVgKL8EQozar="},
    {"key": 43, "value": "nIjaUTDhgL/r4IxrhYKBUzRLrshrJldlVgKL8EQozas="},
    {"key": 44, "value": "nIjaUTDhgL/r4IxrhYKBUzRLrshrJldlVgKL8EQozat="},
    {"key": 45, "value": "nIjaUTDhgL/r4IxrhYKBUzRLrshrJldlVgKL8EQozau="},
    {"key": 46, "value": "nIjaUTDhgL/r4IxrhYKBUzRLrshrJldlVgKL8EQozav="},
    {"key": 47, "value": "nIjaUTDhgL/r4IxrhYKBUzRLrshrJldlVgKL8EQozaw="},
    {"key": 48, "value": "nIjaUTDhgL/r4IxrhYKBUzRLrshrJldlVgKL8EQozax="},
    {"key": 49, "value": "nIjaUTDhgL/r4IxrhYKBUzRLrshrJldlVgKL8EQozay="},
    {"key": 50, "value": "nIjaUTDhgL/r4IxrhYKBUzRLrshrJldlVgKL8EQozaz="},
    {"key": 51, "value": "nIjaUTDhgL/r4IxrhYKBUzRLrshrJldlVgKL8EQozba="},
]

# ─────────────────────────────────────────────
def decode_jwt(token):
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload))
    except Exception:
        return {}

def extract_oob_code(link):
    inner = unquote(link.split("link=")[-1]) if "link=" in link else link
    parsed = urlparse(inner)
    params = parse_qs(parsed.query)
    code = params.get("oobCode", [None])[0]
    if not code:
        match = re.search(r"oobCode=([^&\s]+)", unquote(link))
        code = match.group(1) if match else None
    return code

def generate_chat_id():
    """Generate a Firestore-style 20-char alphanumeric ID matching X_CHAT_ID format."""
    chars = string.ascii_letters + string.digits
    return "".join(random.choices(chars, k=20))

def firebase_headers():
    return {
        "Content-Type":        "application/json",
        "Accept-Encoding":     "gzip",
        "Accept-Language":     "en-US",
        "Connection":          "Keep-Alive",
        "User-Agent":          USER_AGENT_DALVIK,
        "X-Android-Cert":      ANDROID_CERT,
        "X-Android-Package":   ANDROID_PACKAGE,
        "X-Client-Version":    X_CLIENT_VERSION,
        "X-Firebase-AppCheck": X_FIREBASE_APPCHECK,
        "X-Firebase-Client":   X_FIREBASE_CLIENT,
        "X-Firebase-GMPID":    X_FIREBASE_GMPID,
    }

def nova_headers(id_token, user_id, extra=None):
    h = {
        "Content-Type":    "application/json; charset=UTF-8",
        "Accept-Encoding": "gzip",
        "Connection":      "Keep-Alive",
        "User-Agent":      USER_AGENT_OKHTTP,
        "X_DEV":           "false",
        "X_IMAGE_VERSION": "4",
        "X_PLATFORM":      "android",
        "X_PLATFORM_ID":   X_PLATFORM_ID,
        "X_PR":            "false",
        "X_TOKEN":         id_token,
        "X_USER_ID":       user_id,
        "X_VERSION":       "3",
    }
    if extra:
        h.update(extra)
    return h

# ─────────────────────────────────────────────
# MAIN APP
# ─────────────────────────────────────────────

class NovaApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # App state
        self.id_token             = ""
        self.refresh_token        = ""
        self.user_id              = ""
        self.email_val            = ""
        self.authenticated        = False
        self.active_model_id      = None
        self.cf_cookies           = {}
        self.cf_profile           = CF_IMPERSONATE_PROFILES[0]

        # Conversation state — persisted across follow-up messages
        self.conversation_history = []    # list of {role, content, a}
        self.current_chat_id      = None  # reused for the whole conversation
        self.conversation_model   = None  # locked to the model that started the chat

        # Appearance
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("Nova AI — Auth & Chat Replicator  |  Forensic Analysis Tool")
        self.geometry("1100x780")
        self.minsize(900, 650)
        self.configure(fg_color="#0f1117")

        self._build_ui()

    # ─── UI BUILDER ───────────────────────────────────────

    def _build_ui(self):
        # ── Top bar ──────────────────────────────────────
        top = ctk.CTkFrame(self, fg_color="#161b27", height=52, corner_radius=0)
        top.pack(fill="x", side="top")
        top.pack_propagate(False)
        ctk.CTkLabel(top, text="⬡  Nova AI  —  Forensic Auth & Chat Replicator",
                     font=("Consolas", 13, "bold"),
                     text_color="#58a6ff").pack(side="left", padx=18, pady=14)
        self.status_badge = ctk.CTkLabel(top, text="● NOT AUTHENTICATED",
                                         font=("Consolas", 11),
                                         text_color="#f85149")
        self.status_badge.pack(side="right", padx=18)

        # ── Main area ─────────────────────────────────────
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=12, pady=(8, 4))

        # Left column — auth
        left = ctk.CTkFrame(main, fg_color="#161b27", corner_radius=10, width=380)
        left.pack(side="left", fill="y", padx=(0, 6))
        left.pack_propagate(False)
        self._build_auth_panel(left)

        # Right column — chat + log
        right = ctk.CTkFrame(main, fg_color="transparent")
        right.pack(side="left", fill="both", expand=True)
        self._build_chat_panel(right)
        self._build_log_panel(right)

    # ── AUTH PANEL ─────────────────────────────────────────

    def _build_auth_panel(self, parent):
        ctk.CTkLabel(parent, text="AUTHENTICATION",
                     font=("Consolas", 11, "bold"),
                     text_color="#8b949e").pack(anchor="w", padx=16, pady=(14, 2))

        # ── Step 1 ──────────────────────────────────────
        s1 = self._section(parent, "Step 1 — Magic Link")

        ctk.CTkLabel(s1, text="Email address", font=("Consolas", 11),
                     text_color="#8b949e").pack(anchor="w", padx=4, pady=(4, 1))
        self.email_entry = ctk.CTkEntry(s1, placeholder_text="you@example.com",
                                        font=("Consolas", 12), height=34)
        self.email_entry.pack(fill="x", padx=4, pady=(0, 6))

        self.btn_send = ctk.CTkButton(s1, text="Send Magic Link",
                                      font=("Consolas", 12, "bold"),
                                      fg_color="#1f6feb", hover_color="#388bfd",
                                      height=34, command=self._on_send_link)
        self.btn_send.pack(fill="x", padx=4)
        self.lbl_step1 = ctk.CTkLabel(s1, text="", font=("Consolas", 10),
                                       text_color="#8b949e")
        self.lbl_step1.pack(anchor="w", padx=4, pady=(3, 0))

        # ── Step 2 ──────────────────────────────────────
        s2 = self._section(parent, "Step 2 — Sign In")

        ctk.CTkLabel(s2, text="Paste magic link from email",
                     font=("Consolas", 11), text_color="#8b949e").pack(anchor="w", padx=4, pady=(4, 1))
        self.link_entry = ctk.CTkTextbox(s2, height=72, font=("Consolas", 10),
                                          fg_color="#0d1117", border_color="#30363d",
                                          border_width=1)
        self.link_entry.pack(fill="x", padx=4, pady=(0, 6))

        self.btn_signin = ctk.CTkButton(s2, text="Sign In",
                                        font=("Consolas", 12, "bold"),
                                        fg_color="#238636", hover_color="#2ea043",
                                        height=34, command=self._on_signin)
        self.btn_signin.pack(fill="x", padx=4)
        self.lbl_step2 = ctk.CTkLabel(s2, text="", font=("Consolas", 10),
                                       text_color="#8b949e")
        self.lbl_step2.pack(anchor="w", padx=4, pady=(3, 0))

        # ── Session info ─────────────────────────────────
        s3 = self._section(parent, "Session Info")

        labels = ["Firebase UID", "Display Name", "Email", "Nova User ID", "Token TTL"]
        self.info_labels = {}
        for lbl in labels:
            row = ctk.CTkFrame(s3, fg_color="transparent")
            row.pack(fill="x", padx=4, pady=1)
            ctk.CTkLabel(row, text=f"{lbl}:", font=("Consolas", 10),
                         text_color="#8b949e", width=100, anchor="w").pack(side="left")
            val = ctk.CTkLabel(row, text="—", font=("Consolas", 10),
                               text_color="#e6edf3", anchor="w")
            val.pack(side="left", fill="x", expand=True)
            self.info_labels[lbl] = val

        # Manual Nova User ID override (paste from captured traffic)
        ctk.CTkLabel(s3, text="Override Nova User ID (paste from captured traffic):",
                     font=("Consolas", 9), text_color="#8b949e").pack(anchor="w", padx=4, pady=(6, 1))
        override_row = ctk.CTkFrame(s3, fg_color="transparent")
        override_row.pack(fill="x", padx=4, pady=(0, 4))
        self.nova_id_override = ctk.CTkEntry(override_row,
                                              placeholder_text="e.g. 65f9653f1a0768ec929011b1c7220cc0",
                                              font=("Consolas", 10), height=28)
        self.nova_id_override.pack(side="left", fill="x", expand=True, padx=(0, 4))
        ctk.CTkButton(override_row, text="Apply",
                      font=("Consolas", 10),
                      fg_color="#21262d", hover_color="#30363d",
                      border_color="#30363d", border_width=1,
                      width=50, height=28,
                      command=self._apply_nova_id_override).pack(side="left")

        # ── Refresh token ─────────────────────────────────
        s4 = self._section(parent, "Token Management")
        self.btn_refresh = ctk.CTkButton(s4, text="Refresh Token",
                                         font=("Consolas", 11),
                                         fg_color="#21262d", hover_color="#30363d",
                                         border_color="#30363d", border_width=1,
                                         height=30, command=self._on_refresh_token)
        self.btn_refresh.pack(fill="x", padx=4, pady=(4, 2))
        self.btn_save = ctk.CTkButton(s4, text="Save Session  →  session.json",
                                      font=("Consolas", 11),
                                      fg_color="#21262d", hover_color="#30363d",
                                      border_color="#30363d", border_width=1,
                                      height=30, command=self._on_save_session)
        self.btn_save.pack(fill="x", padx=4, pady=(0, 4))

        # ── Display Name ─────────────────────────────────
        s5 = self._section(parent, "Display Name")
        ctk.CTkLabel(s5, text="Change displayName (Firebase accounts:update):",
                     font=("Consolas", 9), text_color="#8b949e").pack(anchor="w", padx=4, pady=(4, 1))
        name_row = ctk.CTkFrame(s5, fg_color="transparent")
        name_row.pack(fill="x", padx=4, pady=(0, 2))
        self.display_name_entry = ctk.CTkEntry(name_row,
                                                placeholder_text="New display name",
                                                font=("Consolas", 11), height=30)
        self.display_name_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self.btn_set_name = ctk.CTkButton(name_row, text="Apply",
                                           font=("Consolas", 11, "bold"),
                                           fg_color="#1f6feb", hover_color="#388bfd",
                                           width=70, height=30,
                                           command=self._on_set_display_name)
        self.btn_set_name.pack(side="left")
        self.lbl_name_status = ctk.CTkLabel(s5, text="",
                                             font=("Consolas", 10),
                                             text_color="#8b949e")
        self.lbl_name_status.pack(anchor="w", padx=4, pady=(2, 0))

    # ── CHAT PANEL ─────────────────────────────────────────

    def _build_chat_panel(self, parent):
        chat_frame = ctk.CTkFrame(parent, fg_color="#161b27", corner_radius=10)
        chat_frame.pack(fill="both", expand=True, pady=(0, 6))

        # Header
        hdr = ctk.CTkFrame(chat_frame, fg_color="transparent")
        hdr.pack(fill="x", padx=14, pady=(10, 4))
        ctk.CTkLabel(hdr, text="CHAT", font=("Consolas", 11, "bold"),
                     text_color="#8b949e").pack(side="left")

        ctk.CTkLabel(hdr, text="Model:", font=("Consolas", 11),
                     text_color="#8b949e").pack(side="left", padx=(12, 4))
        self.model_var = ctk.StringVar(value="GPT-4o Mini  (29)")
        self.model_menu = ctk.CTkOptionMenu(hdr, variable=self.model_var,
                                            values=list(MODEL_OPTIONS.keys()),
                                            font=("Consolas", 11),
                                            fg_color="#21262d",
                                            button_color="#30363d",
                                            width=180,
                                            command=self._on_model_changed)
        self.model_menu.pack(side="left")

        # "Apply Model" button — explicit POST /api/v3/users/{id} to register modelMap
        self.btn_apply_model = ctk.CTkButton(hdr, text="Apply Model",
                                              font=("Consolas", 11, "bold"),
                                              fg_color="#238636", hover_color="#2ea043",
                                              width=100, height=28,
                                              command=self._on_apply_model)
        self.btn_apply_model.pack(side="left", padx=(6, 0))

        # Active model indicator (shows which model has been synced with server)
        self.lbl_active_model = ctk.CTkLabel(hdr, text="● Not synced",
                                              font=("Consolas", 10),
                                              text_color="#8b949e")
        self.lbl_active_model.pack(side="left", padx=(8, 0))

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

        # Chat display
        self.chat_display = ctk.CTkTextbox(chat_frame,
                                            font=("Consolas", 12),
                                            fg_color="#0d1117",
                                            text_color="#e6edf3",
                                            wrap="word",
                                            state="disabled")
        self.chat_display.pack(fill="both", expand=True, padx=14, pady=(0, 8))
        self.chat_display.tag_config("user",     foreground="#58a6ff")
        self.chat_display.tag_config("bot",      foreground="#e6edf3")
        self.chat_display.tag_config("system",   foreground="#8b949e")
        self.chat_display.tag_config("error",    foreground="#f85149")

        # Input row
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

    # ── LOG PANEL ──────────────────────────────────────────

    def _build_log_panel(self, parent):
        log_frame = ctk.CTkFrame(parent, fg_color="#161b27",
                                  corner_radius=10, height=130)
        log_frame.pack(fill="x")
        log_frame.pack_propagate(False)

        ctk.CTkLabel(log_frame, text="REQUEST LOG",
                     font=("Consolas", 10, "bold"),
                     text_color="#8b949e").pack(anchor="w", padx=14, pady=(8, 2))

        self.log_box = ctk.CTkTextbox(log_frame,
                                       font=("Consolas", 10),
                                       fg_color="#0d1117",
                                       text_color="#8b949e",
                                       state="disabled",
                                       height=88)
        self.log_box.pack(fill="both", expand=True, padx=14, pady=(0, 8))

    # ── HELPERS ────────────────────────────────────────────

    def _section(self, parent, title):
        outer = ctk.CTkFrame(parent, fg_color="#0d1117",
                              corner_radius=8, border_color="#21262d",
                              border_width=1)
        outer.pack(fill="x", padx=12, pady=5)
        ctk.CTkLabel(outer, text=title,
                     font=("Consolas", 10, "bold"),
                     text_color="#58a6ff").pack(anchor="w", padx=10, pady=(8, 2))
        inner = ctk.CTkFrame(outer, fg_color="transparent")
        inner.pack(fill="x", padx=6, pady=(0, 8))
        return inner

    def _log(self, msg, level="info"):
        """Thread-safe log — always scheduled on the main UI thread."""
        colors = {"info": "#8b949e", "ok": "#3fb950", "err": "#f85149", "req": "#d2a8ff"}
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

        try:
            self.after(0, _do)
        except Exception:
            pass

    def _chat_append(self, text, tag="system"):
        """Thread-safe chat append."""
        def _do():
            try:
                self.chat_display.configure(state="normal")
                self.chat_display.insert("end", text, tag)
                self.chat_display.see("end")
                self.chat_display.configure(state="disabled")
            except Exception:
                pass

        try:
            self.after(0, _do)
        except Exception:
            pass

    def _ui(self, fn, *args, **kwargs):
        """Schedule any UI callable on the main thread."""
        try:
            self.after(0, lambda: fn(*args, **kwargs))
        except Exception:
            pass

    def _clear_chat(self):
        self.chat_display.configure(state="normal")
        self.chat_display.delete("1.0", "end")
        self.chat_display.configure(state="disabled")

    def _new_conversation(self):
        """Reset conversation state — generates new chat_id on next message."""
        had_history = bool(self.conversation_history)
        self.conversation_history = []
        self.current_chat_id      = None
        self.conversation_model   = None
        self._clear_chat()
        if had_history:
            self._log("New conversation started — history cleared", "ok")
        self._chat_append(
            "[System] New conversation started. A fresh chat_id will be generated on the next message.\n",
            "system"
        )

    def _set_info(self, key, val):
        if key in self.info_labels:
            display = val if len(val) < 36 else val[:33] + "…"
            self._ui(self.info_labels[key].configure, text=display)

    def _set_auth_status(self, ok):
        self.authenticated = ok
        if ok:
            self._ui(self.status_badge.configure,
                     text="● AUTHENTICATED", text_color="#3fb950")
        else:
            self._ui(self.status_badge.configure,
                     text="● NOT AUTHENTICATED", text_color="#f85149")

    def _run_thread(self, fn):
        threading.Thread(target=fn, daemon=True).start()

    # ── AUTH ACTIONS ───────────────────────────────────────

    def _on_send_link(self):
        email = self.email_entry.get().strip()
        if not email:
            messagebox.showwarning("Input", "Enter an email address first.")
            return
        self.email_val = email
        self.btn_send.configure(state="disabled", text="Sending…")
        self._run_thread(self._send_link_thread)

    def _send_link_thread(self):
        self._log(f"POST getOobConfirmationCode [{self.email_val}]", "req")
        url = f"{FIREBASE_BASE}/getOobConfirmationCode?key={FIREBASE_API_KEY}"
        payload = {
            "requestType": 6, "email": self.email_val,
            "androidInstallApp": True, "canHandleCodeInApp": True,
            "continueUrl": "https://auth.novaapp.ai/__/auth/action",
            "iosBundleId": "com.scaleup.chatai",
            "androidPackageName": "com.scaleup.chatai",
            "androidMinimumVersion": "7",
            "linkDomain": "auth.novaapp.ai",
            "clientType": "CLIENT_TYPE_ANDROID",
        }
        try:
            resp = requests.post(url, headers=firebase_headers(), json=payload, timeout=10)
            if resp.status_code == 200:
                self._log(f"Magic link sent to {self.email_val}", "ok")
                self.lbl_step1.configure(text=f"✓ Email sent to {self.email_val}",
                                          text_color="#3fb950")
            else:
                err = resp.json().get("error", {}).get("message", "unknown")
                self._log(f"Step 1 failed: {err}", "err")
                self.lbl_step1.configure(text=f"✗ {err}", text_color="#f85149")
        except Exception as e:
            self._log(f"Request error: {e}", "err")
        finally:
            self._ui(self.btn_send.configure, state="normal", text="Send Magic Link")

    def _on_signin(self):
        email = self.email_entry.get().strip() or self.email_val
        link  = self.link_entry.get("1.0", "end").strip()
        if not email or not link:
            messagebox.showwarning("Input", "Fill in email and paste the magic link.")
            return
        self.email_val = email
        self.btn_signin.configure(state="disabled", text="Signing in…")
        self._run_thread(lambda: self._signin_thread(email, link))

    def _signin_thread(self, email, link):
        oob = extract_oob_code(link)
        if not oob:
            self._log("Could not extract oobCode from link", "err")
            self.lbl_step2.configure(text="✗ Invalid link format", text_color="#f85149")
            self.btn_signin.configure(state="normal", text="Sign In")
            return

        self._log(f"oobCode: {oob[:28]}…", "req")
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithEmailLink?key={FIREBASE_API_KEY}"
        try:
            resp = requests.post(url, headers=firebase_headers(),
                                 json={"email": email, "oobCode": oob}, timeout=10)
            data = resp.json()
            if resp.status_code == 200 and "idToken" in data:
                self.id_token      = data["idToken"]
                self.refresh_token = data["refreshToken"]
                claims = decode_jwt(self.id_token)

                firebase_uid = claims.get("user_id", "")
                self.user_id = firebase_uid

                self._log("Firebase sign-in successful", "ok")
                self._set_auth_status(True)
                self.lbl_step2.configure(text="✓ Signed in", text_color="#3fb950")

                self._set_info("Firebase UID",  firebase_uid)
                current_name = claims.get("name", "")
                self._set_info("Display Name",  current_name or "—")
                self._set_info("Email",          claims.get("email", "—"))
                self._set_info("Nova User ID",   firebase_uid)
                self._set_info("Token TTL",      f"{int(data.get('expiresIn','0'))//60} min")

                # Pre-fill display name entry with current value
                if current_name:
                    self._ui(self.display_name_entry.delete, 0, "end")
                    self._ui(self.display_name_entry.insert, 0, current_name)

                # Try to resolve Nova user ID
                self._run_thread(self._fetch_nova_user)
            else:
                err = data.get("error", {}).get("message", "unknown")
                self._log(f"Sign-in failed: {err}", "err")
                self.lbl_step2.configure(text=f"✗ {err}", text_color="#f85149")
        except Exception as e:
            self._log(f"Request error: {e}", "err")
        finally:
            self.btn_signin.configure(state="normal", text="Sign In")

    def _fetch_nova_user(self):
        """
        Try to resolve the Nova internal user ID dynamically.
        Strategy:
          1. GET /api/v3/users/me  (no X_USER_ID — token-only auth)
          2. POST /api/v3/users/{firebase_uid} and parse response body
          3. GET /api/v3/users/{firebase_uid}
          4. If all fail, prompt the user to enter it manually
        """
        firebase_uid = self.user_id  # starts as Firebase UID from JWT
        resolved = False

        # ── Strategy 1: GET /users/me with token only ────────────────
        self._log("Trying GET /api/v3/users/me (token-only auth)…", "req")
        try:
            headers_no_uid = {k: v for k, v in
                              nova_headers(self.id_token, "").items()
                              if k != "X_USER_ID"}
            resp = cf_requests.get(
                f"{NOVA_API_BASE}/api/v3/users/me",
                headers=headers_no_uid,
                cookies=self.cf_cookies,
                impersonate=self.cf_profile,
                timeout=8,
            ) if HAS_CURL_CFFI else requests.get(
                f"{NOVA_API_BASE}/api/v3/users/me",
                headers=headers_no_uid, timeout=8,
            )
            self._log(f"  → {resp.status_code}", "ok" if resp.status_code == 200 else "info")
            if resp.status_code == 200:
                data = resp.json()
                self._log(f"  body: {json.dumps(data)[:200]}", "info")
                nova_id = (data.get("_id") or data.get("id") or
                           data.get("userId") or data.get("user_id"))
                if nova_id:
                    self.user_id = nova_id
                    self._set_info("Nova User ID", nova_id)
                    self._log(f"Nova user ID from /me: {nova_id}", "ok")
                    resolved = True
        except Exception as e:
            self._log(f"  → exception: {e}", "err")

        # ── Strategy 2: POST /users/{firebase_uid} — parse response ──
        if not resolved:
            self._log("Trying POST /api/v3/users/{firebase_uid} and parsing response…", "req")
            try:
                url = f"{NOVA_API_BASE}/api/v3/users/{firebase_uid}"
                resp = cf_requests.post(
                    url,
                    headers=nova_headers(self.id_token, firebase_uid),
                    json={"fcmToken": "none", "model": MODEL_MAP},
                    cookies=self.cf_cookies,
                    impersonate=self.cf_profile,
                    timeout=10,
                ) if HAS_CURL_CFFI else requests.post(
                    url,
                    headers=nova_headers(self.id_token, firebase_uid),
                    json={"fcmToken": "none", "model": MODEL_MAP},
                    timeout=10,
                )
                self._log(f"  → {resp.status_code}", "ok" if resp.status_code in (200, 201) else "info")
                if resp.status_code in (200, 201):
                    self._log(f"  body: {resp.text[:300]}", "info")
                    try:
                        data = resp.json()
                        nova_id = (data.get("_id") or data.get("id") or
                                   data.get("userId") or data.get("user_id") or
                                   data.get("data", {}).get("_id") or
                                   data.get("data", {}).get("id"))
                        if nova_id and nova_id != firebase_uid:
                            self.user_id = nova_id
                            self._set_info("Nova User ID", nova_id)
                            self._log(f"Nova user ID from setup response: {nova_id}", "ok")
                            resolved = True
                        else:
                            # Setup succeeded — server accepts firebase_uid as user_id
                            self.user_id = firebase_uid
                            self._set_info("Nova User ID", firebase_uid)
                            self._log("Server accepts Firebase UID as user ID", "ok")
                            resolved = True
                    except Exception:
                        self._log(f"  could not parse response: {resp.text[:100]}", "err")
            except Exception as e:
                self._log(f"  → exception: {e}", "err")

        # ── Strategy 3: GET /users/{firebase_uid} ────────────────────
        if not resolved:
            self._log(f"Trying GET /api/v3/users/{firebase_uid[:16]}…", "req")
            try:
                resp = cf_requests.get(
                    f"{NOVA_API_BASE}/api/v3/users/{firebase_uid}",
                    headers=nova_headers(self.id_token, firebase_uid),
                    cookies=self.cf_cookies,
                    impersonate=self.cf_profile,
                    timeout=8,
                ) if HAS_CURL_CFFI else requests.get(
                    f"{NOVA_API_BASE}/api/v3/users/{firebase_uid}",
                    headers=nova_headers(self.id_token, firebase_uid),
                    timeout=8,
                )
                self._log(f"  → {resp.status_code}", "ok" if resp.status_code == 200 else "info")
                if resp.status_code == 200:
                    data = resp.json()
                    self._log(f"  body: {json.dumps(data)[:200]}", "info")
                    nova_id = (data.get("_id") or data.get("id") or
                               data.get("userId") or firebase_uid)
                    self.user_id = nova_id
                    self._set_info("Nova User ID", nova_id)
                    self._log(f"Nova user ID from GET: {nova_id}", "ok")
                    resolved = True
            except Exception as e:
                self._log(f"  → exception: {e}", "err")

        # ── Strategy 4: prompt user for manual input ─────────────────
        if not resolved:
            self._log(
                "Could not resolve Nova user ID automatically.\n"
                "  → Find it in captured traffic (X_USER_ID header)\n"
                "  → Or in device SharedPreferences: KEY_USER_AUTHENTICATION_ID\n"
                "  → Paste it in the Override field and click Apply.",
                "err"
            )
            self._chat_append(
                "\n[Action required] Nova user ID could not be resolved automatically.\n"
                "Paste your Nova User ID in the Override field (Session Info panel)\n"
                "and click Apply before sending a message.\n\n"
                "Where to find it:\n"
                "  • From captured app traffic → X_USER_ID header value\n"
                "  • From device SharedPreferences → KEY_USER_AUTHENTICATION_ID\n",
                "system"
            )
            return  # don't run setup yet — wait for manual input

        # Run setup with resolved ID
        self._setup_user_model()

    def _setup_user_model(self, active_model=None):
        """
        POST /api/v3/users/{userId} — registers modelMap with the server.
        Equivalent to the 'Select LLM' captured request.
        Should be called after login and whenever the user picks a different model.
        The full modelMap is sent every time (server-side it associates the user
        with the encrypted model permission tokens). `active_model` is optional
        and only used for logging / state tracking.
        """
        url = f"{NOVA_API_BASE}/api/v3/users/{self.user_id}"
        payload = {
            "fcmToken": "none",
            "model": MODEL_MAP,
        }
        label = f"model={active_model}" if active_model is not None else "initial"
        self._log(f"POST /api/v3/users/{self.user_id[:16]}…  [{label}]", "req")
        try:
            resp = cf_requests.post(
                url,
                headers=nova_headers(self.id_token, self.user_id),
                json=payload,
                cookies=self.cf_cookies,
                impersonate=self.cf_profile,
                timeout=10,
            ) if HAS_CURL_CFFI else requests.post(
                url,
                headers=nova_headers(self.id_token, self.user_id),
                json=payload,
                timeout=10,
            )
            self._log(f"User setup: {resp.status_code}", "ok" if resp.status_code in (200, 201) else "err")
            if resp.status_code in (200, 201):
                try:
                    data = resp.json()
                    self._log(f"User setup full response: {json.dumps(data)}", "info")
                    inner = data.get("data") or data
                    nova_id = (
                        inner.get("_id") or
                        inner.get("id") or
                        data.get("_id") or
                        data.get("id") or
                        inner.get("userId") or
                        inner.get("user_id")
                    )
                    if nova_id and nova_id != self.user_id:
                        self.user_id = nova_id
                        self._set_info("Nova User ID", nova_id)
                        self._log(f"Nova user ID updated from setup: {nova_id}", "ok")
                    else:
                        self._log(f"Setup returned userId: {inner.get('userId','?')} — no internal _id found", "info")
                except Exception:
                    self._log(f"User setup raw: {resp.text}", "info")
            else:
                self._log(f"Setup body: {resp.text[:200]}", "err")
                raise RuntimeError(f"Setup failed: {resp.status_code}")
        except Exception as e:
            self._log(f"User setup exception: {e}", "err")
            raise

    def _get_token_count(self, message, model_id):
        """
        POST /api/token-count — required pre-call before /api/chat.
        Returns the token count (int) for the message, or None on failure.
        """
        url = f"{NOVA_API_BASE}/api/token-count"
        payload = {"content": message, "model": model_id}
        self._log(f"POST /api/token-count  model={model_id}", "req")
        try:
            resp = cf_requests.post(
                url,
                headers=nova_headers(self.id_token, self.user_id),
                json=payload,
                cookies=self.cf_cookies,
                impersonate=self.cf_profile,
                timeout=10,
            ) if HAS_CURL_CFFI else requests.post(
                url,
                headers=nova_headers(self.id_token, self.user_id),
                json=payload,
                timeout=10,
            )
            self._log(f"Token count: {resp.status_code}", "ok" if resp.status_code == 200 else "err")
            if resp.cookies:
                self.cf_cookies.update(dict(resp.cookies))
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    self._log(f"Token count response: {data}", "info")
                    return data.get("token") or data.get("tokens") or 0
                except Exception:
                    pass
        except Exception as e:
            self._log(f"Token count exception: {e}", "err")
        return None

    def _on_refresh_token(self):
        if not self.refresh_token:
            messagebox.showinfo("Token", "No refresh token available. Sign in first.")
            return
        self._run_thread(self._refresh_thread)

    def _refresh_thread(self):
        self._log("POST securetoken/token [refresh]", "req")
        url = f"{SECURETOKEN_BASE}/token?key={FIREBASE_API_KEY}"
        try:
            resp = requests.post(url, headers={"Content-Type": "application/json"},
                                 json={"grant_type": "refresh_token",
                                       "refresh_token": self.refresh_token}, timeout=10)
            data = resp.json()
            if resp.status_code == 200 and "id_token" in data:
                self.id_token      = data["id_token"]
                self.refresh_token = data.get("refresh_token", self.refresh_token)
                self._log("Token refreshed successfully", "ok")
                self._set_info("Token TTL", f"{int(data.get('expires_in','0'))//60} min")
            else:
                self._log(f"Refresh failed: {data}", "err")
        except Exception as e:
            self._log(f"Request error: {e}", "err")

    def _on_save_session(self):
        if not self.id_token:
            messagebox.showinfo("Session", "No active session to save.")
            return
        session = {
            "email":         self.email_val,
            "user_id":       self.user_id,
            "id_token":      self.id_token,
            "refresh_token": self.refresh_token,
        }
        with open("session.json", "w") as f:
            json.dump(session, f, indent=2)
        messagebox.showinfo("Saved", "Session saved to session.json")
        self._log("Session saved to session.json", "ok")

    def _on_set_display_name(self):
        if not self.authenticated or not self.id_token:
            messagebox.showwarning("Auth", "Sign in first.")
            return
        new_name = self.display_name_entry.get().strip()
        if not new_name:
            messagebox.showwarning("Input", "Enter a display name.")
            return
        self._ui(self.btn_set_name.configure, state="disabled", text="Applying…")
        self._ui(self.lbl_name_status.configure,
                 text="Updating…", text_color="#d29922")
        self._run_thread(lambda: self._set_display_name_thread(new_name))

    def _set_display_name_thread(self, new_name):
        """
        POST /v3/relyingparty/setAccountInfo — matches the Android app exactly.
        The Firebase Android SDK uses the v3 relyingparty endpoint, NOT v1.
        Updates the displayName claim and returns a fresh JWT.
        """
        url = f"{FIREBASE_BASE}/setAccountInfo?key={FIREBASE_API_KEY}"
        payload = {
            "idToken":           self.id_token,
            "displayName":       new_name,
            "returnSecureToken": True,
        }
        self._log(f"POST setAccountInfo displayName='{new_name}'", "req")
        try:
            resp = requests.post(url, headers=firebase_headers(),
                                 json=payload, timeout=10)
            data = resp.json()
            self._log(f"Response {resp.status_code}: {json.dumps(data)[:300]}", "info")

            if resp.status_code == 200 and data.get("displayName"):
                # setAccountInfo always returns the new displayName.
                # idToken is only returned when re-auth happened; otherwise
                # the existing JWT becomes stale but the change is persisted.
                display_name = data.get("displayName") or new_name

                # If a fresh JWT came back, use it; otherwise keep current
                if "idToken" in data:
                    self.id_token      = data["idToken"]
                    self.refresh_token = data.get("refreshToken", self.refresh_token)
                    self._log(f"JWT refreshed inline with new displayName claim", "ok")
                    self._set_info("Token TTL", f"{int(data.get('expiresIn','0'))//60} min")
                else:
                    self._log("No fresh JWT returned — refresh token to update name claim", "info")

                self._log(f"Display name updated → '{display_name}'", "ok")
                self._set_info("Display Name", display_name)
                self._ui(self.lbl_name_status.configure,
                         text=f"✓ Now: {display_name}", text_color="#3fb950")
            else:
                err = data.get("error", {}).get("message", "unknown")
                self._log(f"setAccountInfo failed: {err}", "err")
                self._ui(self.lbl_name_status.configure,
                         text=f"✗ {err}", text_color="#f85149")
        except Exception as e:
            self._log(f"Request error: {e}", "err")
            self._ui(self.lbl_name_status.configure,
                     text=f"✗ {e}", text_color="#f85149")
        finally:
            self._ui(self.btn_set_name.configure, state="normal", text="Apply")

    def _apply_nova_id_override(self):
        val = self.nova_id_override.get().strip()
        if val:
            self.user_id = val
            self._set_info("Nova User ID", val)
            self._log(f"Nova user ID manually set: {val}", "ok")
            # Re-run setup with the correct ID
            self._run_thread(self._setup_user_model)
        else:
            messagebox.showwarning("Input", "Enter a Nova User ID first.")



    def _on_model_changed(self, choice):
        """Called when dropdown value changes — marks state as out-of-sync."""
        if self.authenticated:
            model_id = MODEL_OPTIONS[choice]
            if self.active_model_id != model_id:
                self.lbl_active_model.configure(text="● Not synced", text_color="#d29922")

    def _on_apply_model(self):
        """Explicit model registration with server (POST /api/v3/users/{id})."""
        if not self.authenticated or not self.id_token:
            messagebox.showwarning("Auth", "Authenticate before applying a model.")
            return
        model_id = MODEL_OPTIONS[self.model_var.get()]
        self.lbl_active_model.configure(text="● Syncing…", text_color="#d29922")
        self.btn_apply_model.configure(state="disabled", text="Applying…")
        self._run_thread(lambda: self._apply_model_thread(model_id))

    def _apply_model_thread(self, model_id):
        try:
            self._setup_user_model(active_model=model_id)
            self.active_model_id = model_id
            self.lbl_active_model.configure(
                text=f"● Active: model {model_id}", text_color="#3fb950"
            )
        except Exception as e:
            self._log(f"Apply model failed: {e}", "err")
            self.lbl_active_model.configure(text="● Sync failed", text_color="#f85149")
        finally:
            self.btn_apply_model.configure(state="normal", text="Apply Model")

    def _on_send_message(self):
        if not self.authenticated or not self.id_token:
            messagebox.showwarning("Auth", "You must be authenticated first.")
            return
        msg = self.msg_entry.get().strip()
        if not msg:
            return

        model_id = MODEL_OPTIONS[self.model_var.get()]

        # Warn if changing model mid-conversation — recommend starting fresh
        if (self.conversation_history and
            self.conversation_model is not None and
            self.conversation_model != model_id):
            answer = messagebox.askyesno(
                "Model changed mid-conversation",
                f"This conversation was started with model {self.conversation_model}, "
                f"but you've now selected model {model_id}.\n\n"
                "Continue with the new model on the same conversation? "
                "(Click 'No' to start a new conversation.)"
            )
            if not answer:
                self._new_conversation()

        # Auto-sync model if not yet applied or if user changed dropdown
        if self.active_model_id != model_id:
            self._log(f"Model not synced (active={self.active_model_id}, want={model_id}) — auto-applying", "info")
            self._chat_append(f"\n[System] Auto-applying model {model_id}…\n", "system")
            self._setup_user_model(active_model=model_id)
            self.active_model_id = model_id
            self.lbl_active_model.configure(
                text=f"● Active: model {model_id}", text_color="#3fb950"
            )

        self.msg_entry.delete(0, "end")
        self._chat_append(f"\n[You]  {msg}\n", "user")
        self._chat_append(f"[Nova] ", "system")
        self.btn_send_msg.configure(state="disabled", text="…")
        self._run_thread(lambda: self._chat_thread(msg, model_id))

    def _chat_thread(self, message, model_id):
        if not HAS_CURL_CFFI:
            self._chat_append(
                "\n[Error] curl_cffi not installed.\n"
                "Run: pip install curl_cffi\n", "error"
            )
            self.btn_send_msg.configure(state="normal", text="Send ▶")
            return

        # ── Step A: token-count for the new user message ─────────────
        user_token_count = self._get_token_count(message, model_id)
        if user_token_count is None:
            user_token_count = 0
            self._log("Token count failed — defaulting to 0", "info")

        # ── Step B: chat_id — reuse for follow-ups, generate for new ─
        if self.current_chat_id is None:
            self.current_chat_id = generate_chat_id()
            self.conversation_model = model_id
            self._log(f"New conversation — chat_id: {self.current_chat_id}", "ok")
        else:
            self._log(f"Continuing conversation — chat_id: {self.current_chat_id}", "info")

        chat_id = self.current_chat_id

        # ── Step C: build messages payload with history ──────────────
        # Each historical message has an `a` field (token/char count).
        # The CURRENT (new) user message has NO `a` field.
        messages = list(self.conversation_history) + [
            {"content": message, "role": "user"}    # current msg, no `a`
        ]

        # X_TOKEN_COUNT = sum of all `a` values in history
        cumulative_tokens = sum(m.get("a", 0) for m in self.conversation_history)

        # ── Step D: build and send the chat request ──────────────────
        url = f"{NOVA_API_BASE}/api/chat"
        headers = nova_headers(self.id_token, self.user_id, {
            "Accept":                  "text/event-stream",
            "Content-Type":            "application/json; charset=utf-8",
            "X_CHAT_ID":               chat_id,
            "X_MODEL":                 str(model_id),
            "X_STREAM":                "true",
            "X_SEARCH":                "false",
            "X_FUNCTION_USE":          "true",
            "X_FUNCTION_STATUS":       "false",
            "X_CROSS_MODEL":           "false",
            "X_CROSS_PDF_MODEL":       "true",
            "X_CROSS_ASSISTANT_MODEL": "true",
            "X_TOKEN_COUNT":           str(cumulative_tokens),
            "X_WEB_SEARCH_SOURCE":     "0",
        })
        payload = {
            "messages": messages,
            "modelMap": MODEL_MAP,
        }
        self._log(
            f"Chat: chat_id={chat_id}  history={len(self.conversation_history)} msgs  "
            f"X_TOKEN_COUNT={cumulative_tokens}",
            "info"
        )

        for profile in CF_IMPERSONATE_PROFILES:
            self._log(f"POST /api/chat  model={model_id}  profile={profile}", "req")
            try:
                resp = cf_requests.post(
                    url,
                    headers=headers,
                    json=payload,
                    cookies=self.cf_cookies,
                    stream=True,
                    timeout=30,
                    impersonate=profile,
                )
                self._log(
                    f"Status: {resp.status_code}  profile={profile}",
                    "ok" if resp.status_code == 200 else "err"
                )

                if resp.status_code == 403 and "Just a moment" in resp.text:
                    self._log(f"Cloudflare blocked {profile}, trying next…", "err")
                    continue

                if resp.cookies:
                    self.cf_cookies.update(dict(resp.cookies))
                    self.cf_profile = profile

                if resp.status_code == 200:
                    # Parse the stream and capture the full assistant response
                    assistant_text = self._parse_sse_stream(resp)

                    # Append both messages to history with their `a` values:
                    #   user → a = token_count from /api/token-count
                    #   assistant → a = len(response)  (matches captured data)
                    self.conversation_history.append({
                        "a": user_token_count,
                        "content": message,
                        "role": "user",
                    })
                    if assistant_text:
                        self.conversation_history.append({
                            "a": len(assistant_text),
                            "content": assistant_text,
                            "role": "assistant",
                        })
                    self._log(
                        f"History updated — {len(self.conversation_history)} messages, "
                        f"cumulative tokens={sum(m.get('a',0) for m in self.conversation_history)}",
                        "info"
                    )
                    return

                # Log response headers and full body to diagnose
                custom_err = resp.headers.get("custom-error-code", "none")
                self._log(f"custom-error-code: {custom_err}", "err")

                # With stream=True curl_cffi may not auto-load body — read it explicitly
                try:
                    raw = b"".join(resp.iter_content(chunk_size=4096))
                    err_body = raw.decode("utf-8", errors="replace")
                except Exception:
                    err_body = resp.text or ""

                self._log(f"Response headers: {dict(resp.headers)}", "info")
                self._log(f"Full error body ({len(err_body)} chars): '{err_body}'", "err")
                self._chat_append(
                    f"\n[Error {resp.status_code}  code={custom_err}]\n"
                    f"{err_body or '(empty body)'}\n", "error"
                )
                return

            except Exception as e:
                self._log(f"Exception profile={profile}: {e}", "err")
                continue

        self._chat_append(
            "\n[Error] All TLS profiles blocked by Cloudflare.\n", "error"
        )

    def _parse_sse_stream(self, resp):
        """Parse SSE stream, append content to chat, and return full text."""
        chunks_received = 0
        bytes_total     = 0
        formats_seen    = set()
        full_text       = []
        try:
            for line in resp.iter_lines():
                if not line:
                    continue
                decoded = line if isinstance(line, str) else line.decode("utf-8", errors="replace")
                bytes_total += len(decoded)
                chunks_received += 1

                if chunks_received <= 5:
                    self._log(f"  [chunk {chunks_received}] {decoded[:200]}", "info")

                data_str = None
                if decoded.startswith("data:"):
                    data_str = decoded[5:].strip()
                    formats_seen.add("data:")
                elif decoded.startswith("event:"):
                    formats_seen.add("event:")
                    continue
                elif decoded.startswith(":"):
                    continue
                elif decoded.startswith("{") or decoded.startswith("["):
                    data_str = decoded
                    formats_seen.add("ndjson")
                else:
                    data_str = decoded
                    formats_seen.add("plain")

                if not data_str or data_str == "[DONE]":
                    continue

                try:
                    chunk = json.loads(data_str)
                    content = (
                        chunk.get("content") or
                        chunk.get("text") or
                        chunk.get("message") or
                        chunk.get("data") or
                        chunk.get("response") or
                        (chunk.get("delta", {}) or {}).get("content") or
                        (chunk.get("choices", [{}])[0].get("delta", {}) or {}).get("content") or
                        (chunk.get("choices", [{}])[0].get("message", {}) or {}).get("content") or
                        ""
                    )
                    if content:
                        self._chat_append(content, "bot")
                        full_text.append(content)
                    elif chunks_received <= 5:
                        self._log(f"  [chunk {chunks_received} parsed but no content] keys={list(chunk.keys())}", "info")
                except json.JSONDecodeError:
                    if data_str:
                        self._chat_append(data_str, "bot")
                        full_text.append(data_str)
        except Exception as e:
            self._chat_append(f"\n[Stream error] {e}\n", "error")
            self._log(f"Stream exception: {e}", "err")
        finally:
            self._chat_append("\n", "system")
            self._log(
                f"Stream completed — {chunks_received} chunks, {bytes_total} bytes, formats: {formats_seen or 'none'}",
                "ok"
            )
            self.btn_send_msg.configure(state="normal", text="Send ▶")

        return "".join(full_text)


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    app = NovaApp()
    app.mainloop()