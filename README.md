# Nova AI – Chatbot Requests Replication

Replication of the network requests made by the **Nova AI – Chatbot** Android
application, produced as part of a mobile-application traffic analysis study.
The goal is purely **educational / research-oriented**: to document and
reproduce the HTTP flows observed when capturing the app's traffic, in order to
understand how the client communicates with its backend.

> **Disclaimer**
> This project is intended for educational and research purposes only, to study
> the communication patterns of a third-party application. It uses **no bundled
> secrets** — you must supply your own captured credentials. Use it only against
> services you are authorised to test, and respect the application's Terms of
> Service and all applicable laws.

---

## Contents

| Path | Description |
|------|-------------|
| `bruno/Nova AI - Chatbot/` | [Bruno](https://www.usebruno.com/) API collection with the individual requests, for manual inspection and replay. |
| `requests_replicator_app/` | GUI application (CustomTkinter) that replicates the captured flows interactively. |
| `LICENSE` | GPL-3.0 license. |

---

## Replicated flows

The analysis identified two main flows triggered during normal use of the app.

### 1. Open the application (*Abrir a aplicação*)

Two requests fire when the app launches:

| Method | Endpoint | Notes |
|--------|----------|-------|
| `GET`  | `api.novaapp.ai/api/android/userstatus` | Returns a JSON with a `data` field and a `timestamp`. In all captures the value observed was `"false"`; its purpose was not identified. |
| `POST` | `api.novaapp.ai/api/v3/users/{userId}` | Returns subscription state (`isPremium`), maximum limits (`totalCredit...`) and remaining credits (`credit...`, `mediaCredit...`, `voiceTokenCredit...`). |

### 2. Start a conversation (*Iniciar conversa*)

| Method | Endpoint | Notes |
|--------|----------|-------|
| `POST` | `api.novaapp.ai/api/chat/title` | Creates a new chatbot session. The body carries the model number and the prompt; the response is a generated conversation title. |
| `POST` | `api.novaapp.ai/api/chat` | Sends the initial prompt and returns the chatbot's reply. |

---

## Required parameters

The requests above require authentication values that are **captured from a
real session** — none are hardcoded in this project:

- **`userId`** — a device-unique identifier used in the `/api/v3/users/{userId}` URL.
- **`X_TOKEN`** — a token obtained only from a real request, valid for **~1 hour**.

The following non-sensitive headers are also needed for replication:

- `X_PLATFORM: android`
- `X_PR: false`

---

## The replicator app

`requests_replicator_app/` provides a small desktop GUI that walks through the
two flows. You paste your own `userId` and `X_TOKEN`, then:

- **Run the open-app flow** — issues `userstatus` and `users/{userId}` and shows
  the returned status / premium info.
- **Start a conversation** — pick a model number, type a message, and the app
  calls `chat/title` followed by `chat`, rendering the streamed response.

An optional `modelMap` (captured separately) can be loaded from a JSON file if
your traffic requires it; it is not bundled with the project.

### Requirements

```bash
pip install customtkinter requests curl_cffi
```

`curl_cffi` usage  — it enables TLS impersonation so the
client can pass through Cloudflare in the same way the app does. Without it, the
script falls back to plain `requests`.

### Running

```bash
python requests_replicator_app/nova_gui_anonimo.py
```



Then, in the GUI:

1. Paste your captured **`User_ID`** and **`X_TOKEN`** and click **Apply Credentials**.
2. Click **Run Open-App Flow**.
3. Choose a model number, type a message, and send.

---

## Bruno collection

The `bruno/Nova AI - Chatbot/` folder contains the same requests as a Bruno
collection, so each call can be inspected and replayed individually. Open the
folder in Bruno and provide your own environment variables (e.g. `X_TOKEN`,
`userId`) before sending.

---

## License

Distributed under the **GPL-3.0** license. See [`LICENSE`](LICENSE) for details.
