# SDLC Copilot Bridge (VS Code extension)

A tiny VS Code extension that exposes the **Language Model API** (the same
models Copilot Chat uses) on `http://127.0.0.1:6789/complete` so the SDLC
Agent Python backbone can use GitHub Copilot for Stage 2 user-story
generation without an Anthropic API key.

> **Demo / RFP use only.** Synthetic BRDs go to GitHub Copilot per your
> Copilot tier's data policy. Do not point this at real customer data
> unless your org permits.

## Install (development mode)

```powershell
cd vscode-bridge
npm install
npm run compile

# Open this folder in a new VS Code window and press F5,
# or sideload the compiled extension:
code --install-extension .   # only works after packaging with vsce
```

Easiest path: open the `vscode-bridge` folder in VS Code, press **F5** to
launch an Extension Development Host. The status bar in that host window
shows `🔌 SDLC Bridge :6789`.

## Endpoints

- `GET  /health`     → `{ "ok": true, "service": "sdlc-copilot-bridge" }`
- `POST /complete`   → body `{ "system": "...", "user": "...", "modelFamily": "claude-3.5-sonnet" }`
  - Returns `{ "ok": true, "text": "...", "model": "copilot/claude-3.5-sonnet" }`

Only loopback (`127.0.0.1`) is accepted.

## Settings

| Key | Default | Notes |
|---|---|---|
| `sdlcCopilotBridge.port` | `6789` | Loopback port |
| `sdlcCopilotBridge.modelFamily` | `claude-3.5-sonnet` | Falls back to any Copilot model if unavailable |

## First-use consent

VS Code will prompt you once to authorize this extension to use Copilot.
Click **Allow**.
