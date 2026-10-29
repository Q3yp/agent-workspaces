# /// script
# requires-python = ">=3.11"
# dependencies = ["PyYAML==6.0.3", "tomlkit==0.13.3", "websockets==15.0.1"]
# ///

import argparse
from contextlib import ExitStack
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import threading

import tomlkit
import yaml
from websockets.exceptions import WebSocketException
from websockets.sync.client import connect


def read_workspace(path):
    folder = Path(path).expanduser().resolve(strict=True)
    source = folder / "AGENTS.md"
    text = source.read_text()
    match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)", text, re.S)
    if not match:
        raise ValueError(f"{source}: add YAML frontmatter with name and description")
    metadata = yaml.safe_load(match[1])
    if not isinstance(metadata, dict):
        raise ValueError(f"{source}: frontmatter must be a mapping")
    name = metadata.get("name")
    description = metadata.get("description")
    if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
        raise ValueError(f"{source}: name must use lowercase words separated by hyphens")
    if not isinstance(description, str) or not description.strip() or len(description.splitlines()) != 1:
        raise ValueError(f"{source}: description must be one nonempty line")
    return {"name": name, "description": description.strip(), "path": str(folder)}, text


def change_thread_root(thread_id, root, socket_path, url):
    with ExitStack() as stack:
        if url:
            connection = stack.enter_context(connect(url, open_timeout=15))
            send = connection.send
            receive = lambda: connection.recv(timeout=15)
        else:
            executable = shutil.which("codex.cmd" if os.name == "nt" else "codex")
            if executable is None:
                raise ValueError("Codex CLI is required to change the thread root")
            command = [executable, "app-server", "proxy"]
            if socket_path:
                command.extend(["--sock", socket_path])
            process = stack.enter_context(subprocess.Popen(
                command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True, encoding="utf-8"))
            stack.callback(process.terminate)
            timer = threading.Timer(15, process.kill)
            timer.start()
            stack.callback(timer.cancel)

            def send(message):
                process.stdin.write(message + "\n")
                process.stdin.flush()

            def receive():
                line = process.stdout.readline()
                if not line:
                    raise ValueError("Codex control connection closed or timed out: " + process.stderr.read().strip())
                return line

        def request(identifier, method, params):
            send(json.dumps({"id": identifier, "method": method, "params": params}))
            while True:
                response = json.loads(receive())
                if response.get("id") == identifier:
                    if "error" in response:
                        raise ValueError(f"{method}: {response['error']['message']}")
                    return response["result"]

        request(1, "initialize", {
            "clientInfo": {"name": "agent-workspaces", "version": "0.2.0"},
            "capabilities": {"experimentalApi": True},
        })
        send('{"method":"initialized"}')
        request(2, "thread/settings/update", {"threadId": thread_id, "cwd": root})


def main():
    parser = argparse.ArgumentParser(description="Register and activate local workspaces, independently of skills.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="Read names and descriptions from registered folders")
    commands.add_parser("context", help="Emit the session-start workspace catalog")
    commands.add_parser("add", help="Register a folder and grant future workspace-write sessions access").add_argument("path")
    commands.add_parser("remove", help="Unregister a folder and revoke only the grant added by this plugin").add_argument("path")
    activate = commands.add_parser("activate", help="Set the Codex thread root for subsequent turns and read live instructions")
    activate.add_argument("name")
    activate.add_argument("--thread-id", default=os.environ.get("CODEX_THREAD_ID"))
    endpoint = activate.add_mutually_exclusive_group()
    endpoint.add_argument("--socket", help="Control socket of the app-server hosting this thread (defaults to the Codex daemon)")
    endpoint.add_argument("--url", help="WebSocket endpoint of the app-server hosting this thread")
    args = parser.parse_args()
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser().resolve()
    registry = codex_home / "workspaces.json"
    entries = json.loads(registry.read_text()) if registry.exists() else []
    if not isinstance(entries, list) or any(
        not isinstance(entry, dict)
        or not isinstance(entry.get("path"), str)
        or not isinstance(entry.get("granted_write"), bool)
        for entry in entries
    ):
        raise ValueError(f"{registry}: expected workspace path/granted_write entries")

    if args.command in ("add", "remove"):
        path = str(Path(args.path).expanduser().resolve())
        config_path = codex_home / "config.toml"
        config = tomlkit.parse(config_path.read_text()) if config_path.exists() else tomlkit.document()
        sandbox = config.get("sandbox_workspace_write", {})
        roots = list(sandbox.get("writable_roots", []))
        existing = next((entry for entry in entries if entry["path"] == path), None)
        if args.command == "add":
            workspace, _ = read_workspace(path)
            for entry in entries:
                if entry["path"] != path and read_workspace(entry["path"])[0]["name"] == workspace["name"]:
                    raise ValueError(f"Workspace name already registered: {workspace['name']}")
            if existing is None:
                existing = {"path": path, "granted_write": path not in roots}
                entries.append(existing)
            if path not in roots:
                roots.append(path)
                existing["granted_write"] = True
        else:
            if existing is None:
                raise ValueError(f"Workspace is not registered: {path}")
            entries.remove(existing)
            if existing["granted_write"]:
                roots = [root for root in roots if root != path]
        if roots != list(sandbox.get("writable_roots", [])):
            if "sandbox_workspace_write" not in config:
                config["sandbox_workspace_write"] = tomlkit.table()
            config["sandbox_workspace_write"]["writable_roots"] = roots
            codex_home.mkdir(parents=True, exist_ok=True)
            config_path.write_text(tomlkit.dumps(config))
        codex_home.mkdir(parents=True, exist_ok=True)
        registry.write_text(json.dumps(entries, indent=2) + "\n")
        print(f"{'Registered' if args.command == 'add' else 'Removed'}: {path}")
        print("Start a new session for catalog and write-access changes. Host permission restrictions still apply.")
        return

    workspaces = []
    errors = []
    for entry in entries:
        try:
            workspace, text = read_workspace(entry["path"])
            if any(item[0]["name"] == workspace["name"] for item in workspaces):
                raise ValueError(f"Duplicate workspace name: {workspace['name']}")
            workspaces.append((workspace, text))
        except (OSError, ValueError, yaml.YAMLError) as error:
            errors.append(str(error))

    if args.command == "activate":
        if errors:
            raise ValueError("\n".join(errors))
        selected = next((item for item in workspaces if item[0]["name"] == args.name), None)
        if selected is None:
            raise ValueError(f"Workspace not found: {args.name}. Run list to see registered workspaces.")
        workspace, text = selected
        if not args.thread_id:
            raise ValueError("Activation requires CODEX_THREAD_ID or --thread-id for the existing Codex thread")
        change_thread_root(args.thread_id, workspace["path"], args.socket, args.url)
        print(f"Workspace: {workspace['name']}\nRoot set for subsequent turns: {workspace['path']}\nCurrent tool process directory: {Path.cwd()}\n")
        print("Codex accepted the root update. It takes effect next turn, not after this tool call. "
              "End this initialization turn now; begin workspace work in the next turn. "
              "A host that explicitly supplies cwd on later turns can override this setting.\n")
        print(f"Source: {workspace['path']}/AGENTS.md\n\n{text}", end="")
        return

    if args.command == "list":
        print(json.dumps({"workspaces": [item[0] for item in workspaces], "errors": errors}, indent=2))
        if errors:
            sys.exit(1)
        return

    command = "uv run --offline --script " + shlex.quote(str(Path(__file__).resolve()))
    context = (
        "## Workspaces\n\n"
        "Workspaces hold instructions for a body of work and coexist with the available skills. "
        "Select a workspace by its description when it matches the user's task. "
        f"Activate it by running `{command} activate NAME` to set the existing Codex thread's root for subsequent turns and read its current AGENTS.md. "
        "After successful activation, end the initialization turn; workspace work starts next turn in the new root. "
        "Activation requires a reachable control socket or WebSocket endpoint for the app-server hosting this thread and does not grant permissions. "
        "Apply workspace instructions within that work's scope and use skills normally. "
        "Read linked guidelines as needed. Read the live file again when the user changes its instructions. "
        "Keep work-specific learning in the workspace's appropriate instruction file only when the user asks to save it.\n\n"
        f"Manage registrations with `{command} add PATH`, `remove PATH`, or `list`. "
        "Registration changes write access for future workspace-write sessions. Register only folders the user authorizes.\n\n"
        + json.dumps([item[0] for item in workspaces], ensure_ascii=False, indent=2)
    )
    if errors:
        context += "\n\nWorkspace registration errors:\n" + "\n".join(errors)
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": context}}))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, WebSocketException, yaml.YAMLError) as error:
        sys.exit(f"workspaces: {error}")
