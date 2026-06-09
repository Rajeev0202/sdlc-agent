import * as http from "http";
import * as vscode from "vscode";

let server: http.Server | undefined;
let statusItem: vscode.StatusBarItem | undefined;

interface CompleteRequest {
  system?: string;
  user: string;
  maxTokens?: number;
  modelFamily?: string;
}

async function readBody(req: http.IncomingMessage): Promise<string> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = [];
    req.on("data", (c) => chunks.push(Buffer.from(c)));
    req.on("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
    req.on("error", reject);
  });
}

async function callCopilot(
  body: CompleteRequest
): Promise<{ ok: true; text: string; model: string } | { ok: false; error: string }> {
  const family =
    body.modelFamily ||
    vscode.workspace.getConfiguration("sdlcCopilotBridge").get<string>("modelFamily") ||
    "claude-3.5-sonnet";

  let models = await vscode.lm.selectChatModels({ vendor: "copilot", family });
  if (models.length === 0) {
    // Fallback: pick any available Copilot model.
    models = await vscode.lm.selectChatModels({ vendor: "copilot" });
  }
  if (models.length === 0) {
    return { ok: false, error: "No Copilot chat models available." };
  }

  const model = models[0];
  const messages: vscode.LanguageModelChatMessage[] = [];
  if (body.system) {
    messages.push(vscode.LanguageModelChatMessage.User(`[SYSTEM]\n${body.system}`));
  }
  messages.push(vscode.LanguageModelChatMessage.User(body.user));

  try {
    const response = await model.sendRequest(
      messages,
      { justification: "SDLC Agent demo: generate user stories from a synthetic BRD." },
      new vscode.CancellationTokenSource().token
    );
    let text = "";
    for await (const fragment of response.text) {
      text += fragment;
    }
    return { ok: true, text, model: `${model.vendor}/${model.family}` };
  } catch (err: any) {
    const message = err?.message ?? String(err);
    if (/consent|permission|NoPermissions/i.test(message)) {
      void vscode.window.showWarningMessage(
        "SDLC Bridge: Copilot consent not granted. Run command 'SDLC Bridge: Authorize Copilot'."
      );
    }
    return { ok: false, error: message };
  }
}

async function authorizeCopilot(): Promise<void> {
  try {
    const family =
      vscode.workspace.getConfiguration("sdlcCopilotBridge").get<string>("modelFamily") ||
      "claude-3.5-sonnet";
    let models = await vscode.lm.selectChatModels({ vendor: "copilot", family });
    if (models.length === 0) {
      models = await vscode.lm.selectChatModels({ vendor: "copilot" });
    }
    if (models.length === 0) {
      void vscode.window.showErrorMessage(
        "SDLC Bridge: No Copilot chat models available. Sign in to GitHub Copilot first."
      );
      return;
    }
    const model = models[0];
    const response = await model.sendRequest(
      [vscode.LanguageModelChatMessage.User("Reply with the single word: ok")],
      { justification: "SDLC Agent demo: one-time consent for Stage 2 story generation." },
      new vscode.CancellationTokenSource().token
    );
    let text = "";
    for await (const fragment of response.text) {
      text += fragment;
    }
    void vscode.window.showInformationMessage(
      `SDLC Bridge authorized for ${model.vendor}/${model.family}. Test reply: "${text.trim().slice(0, 40)}"`
    );
  } catch (err: any) {
    void vscode.window.showErrorMessage(
      `SDLC Bridge authorization failed: ${err?.message ?? String(err)}`
    );
  }
}

function startServer(port: number) {
  if (server) {
    server.close();
    server = undefined;
  }

  server = http.createServer(async (req, res) => {
    // Only loopback connections allowed.
    const remote = req.socket.remoteAddress ?? "";
    if (!["127.0.0.1", "::1", "::ffff:127.0.0.1"].includes(remote)) {
      res.writeHead(403).end("forbidden");
      return;
    }

    if (req.method === "GET" && req.url === "/health") {
      res.writeHead(200, { "content-type": "application/json" });
      res.end(JSON.stringify({ ok: true, service: "sdlc-copilot-bridge" }));
      return;
    }

    if (req.method !== "POST" || req.url !== "/complete") {
      res.writeHead(404).end("not found");
      return;
    }

    try {
      const raw = await readBody(req);
      const body = JSON.parse(raw) as CompleteRequest;
      if (!body || typeof body.user !== "string") {
        res.writeHead(400, { "content-type": "application/json" });
        res.end(JSON.stringify({ ok: false, error: "missing 'user' field" }));
        return;
      }
      const result = await callCopilot(body);
      res.writeHead(result.ok ? 200 : 502, { "content-type": "application/json" });
      res.end(JSON.stringify(result));
    } catch (err: any) {
      res.writeHead(500, { "content-type": "application/json" });
      res.end(JSON.stringify({ ok: false, error: err?.message ?? String(err) }));
    }
  });

  server.listen(port, "127.0.0.1", () => {
    if (statusItem) {
      statusItem.text = `$(plug) SDLC Bridge :${port}`;
      statusItem.tooltip = `SDLC Copilot Bridge listening on http://127.0.0.1:${port}`;
      statusItem.show();
    }
    vscode.window.showInformationMessage(
      `SDLC Copilot Bridge listening on http://127.0.0.1:${port}`
    );
  });

  server.on("error", (err) => {
    vscode.window.showErrorMessage(`SDLC Bridge failed: ${err.message}`);
  });
}

export function activate(context: vscode.ExtensionContext) {
  const cfg = vscode.workspace.getConfiguration("sdlcCopilotBridge");
  const port = cfg.get<number>("port") ?? 6789;

  statusItem = vscode.window.createStatusBarItem(
    vscode.StatusBarAlignment.Right,
    100
  );
  context.subscriptions.push(statusItem);

  startServer(port);

  context.subscriptions.push(
    vscode.commands.registerCommand("sdlcCopilotBridge.restart", () => {
      const p =
        vscode.workspace
          .getConfiguration("sdlcCopilotBridge")
          .get<number>("port") ?? 6789;
      startServer(p);
    }),
    vscode.commands.registerCommand("sdlcCopilotBridge.status", () => {
      vscode.window.showInformationMessage(
        server
          ? `SDLC Bridge listening on :${port}`
          : "SDLC Bridge is not running."
      );
    }),
    vscode.commands.registerCommand(
      "sdlcCopilotBridge.authorize",
      authorizeCopilot
    )
  );
}

export function deactivate() {
  if (server) {
    server.close();
    server = undefined;
  }
}
