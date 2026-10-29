# /// script
# requires-python = ">=3.11"
# dependencies = ["PyYAML==6.0.3"]
# ///

import argparse
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
from uuid import UUID

import yaml


def read_workspace(path):
    folder = Path(path).expanduser().resolve(strict=True)
    source = folder / "AGENTS.md"
    text = source.read_text(encoding="utf-8")
    match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)", text, re.S)
    if not match:
        raise ValueError(f"{source}: add YAML frontmatter with name and description")
    metadata = yaml.safe_load(match[1])
    if not isinstance(metadata, dict):
        raise ValueError(f"{source}: frontmatter must be a mapping")
    name, description = metadata.get("name"), metadata.get("description")
    if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
        raise ValueError(f"{source}: name must use lowercase words separated by hyphens")
    if not isinstance(description, str) or not description.strip() or len(description.splitlines()) != 1:
        raise ValueError(f"{source}: description must be one nonempty line")
    return {"name": name, "description": description.strip(), "path": str(folder)}, text


def main():
    parser = argparse.ArgumentParser(description="Antigravity workspace directory selection (native root unchanged).")
    parser.add_argument("--home", type=Path, default=Path(os.environ.get("GEMINI_HOME", Path.home() / ".gemini")))
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("list", "context"):
        commands.add_parser(command)
    for command in ("add", "remove"):
        commands.add_parser(command).add_argument("path")
    activate = commands.add_parser("activate")
    activate.add_argument("name")
    activate.add_argument("--session", required=True, type=UUID)
    clear = commands.add_parser("clear")
    clear.add_argument("--session", required=True, type=UUID)
    install = commands.add_parser("install", help="Install native hooks in this Gemini home; preserve registrations")
    install.add_argument("--acp", action="store_true", help="Install the ACP prompt bridge instead of global hooks")
    install.add_argument("--launcher", type=Path, help="T3's existing agy-user-instructions.cjs launcher")
    args = parser.parse_args()
    home = args.home.expanduser().resolve()
    data = home / "agent-workspaces"
    registry = data / "workspaces.json"
    script = Path(__file__).resolve()
    uv = shutil.which("uv")
    if uv is None:
        raise ValueError("uv must be on PATH")
    quote = subprocess.list2cmdline if os.name == "nt" else shlex.join

    if args.command == "install":
        if args.acp and not args.launcher:
            raise ValueError("--acp requires --launcher pointing to agy-user-instructions.cjs")
        if args.acp:
            launcher = args.launcher.resolve(strict=True)
            launcher_text = launcher.read_text(encoding="utf-8")
            anchor = "  if (!child.stdin.write(`${line}\\n`)) input.pause();"
            if anchor not in launcher_text:
                raise ValueError(f"{launcher}: expected ACP forwarding statement was not found")
        target = home / "config" / "plugins" / "workspaces"
        target.mkdir(parents=True, exist_ok=True)
        for name in ("plugin.json", "workspaces.py", "README.md", "acp-bridge.cjs"):
            source = script.parent / name
            destination = target / name
            if source != destination:
                shutil.copy2(source, destination)
        command = [Path(uv).as_posix(), "run", "--offline", "--script", (target / "workspaces.py").as_posix(), "--home", home.as_posix()]
        hooks = {"agent-workspaces": {
            "PreInvocation": [{"type": "command", "command": shlex.join(command + ["context"])}],
        }}
        (target / "hooks.json").write_text(json.dumps(hooks, indent=2) + "\n", encoding="utf-8")
        if args.acp:
            (target / "acp-command.json").write_text(json.dumps(command), encoding="utf-8")
            bridge_line = "  line = JSON.stringify(require(" + json.dumps((target / "acp-bridge.cjs").as_posix()) + ")(message)); // agent-workspaces"
            backup = launcher.with_suffix(".cjs.before-workspaces")
            if not backup.exists():
                shutil.copy2(launcher, backup)
            launcher_text = "\n".join(line for line in launcher_text.splitlines() if not line.endswith("// agent-workspaces")) + "\n"
            launcher.write_text(launcher_text.replace(anchor, bridge_line + "\n" + anchor), encoding="utf-8")
            config_path = home / "config" / "hooks.json"
            if config_path.exists():
                config = json.loads(config_path.read_text(encoding="utf-8"))
                config.pop("agent-workspaces", None)
                config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        print(f"Installed: {target}\nNew Antigravity sessions load the plugin. Existing processes may need restarting.")
        return

    entries = json.loads(registry.read_text(encoding="utf-8")) if registry.exists() else []
    if not isinstance(entries, list) or any(not isinstance(entry, str) for entry in entries):
        raise ValueError(f"{registry}: expected an array of absolute workspace paths")
    if args.command in ("add", "remove"):
        path = str(Path(args.path).expanduser().resolve())
        if args.command == "add":
            workspace, _ = read_workspace(path)
            for entry in entries:
                if entry != path and read_workspace(entry)[0]["name"] == workspace["name"]:
                    raise ValueError(f"Workspace name already registered: {workspace['name']}")
            if path not in entries:
                entries.append(path)
        else:
            if path not in entries:
                raise ValueError(f"Workspace is not registered: {path}")
            entries.remove(path)
        data.mkdir(parents=True, exist_ok=True)
        registry.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
        print(f"{'Registered' if args.command == 'add' else 'Removed'}: {path}\nFilesystem permissions are unchanged.")
        return

    if args.command == "clear":
        (data / "sessions" / f"{args.session}.json").unlink(missing_ok=True)
        print("Workspace selection cleared. Use the host's original working directory.")
        return

    workspaces, errors = [], []
    for entry in entries:
        try:
            workspace, text = read_workspace(entry)
            if any(item[0]["name"] == workspace["name"] for item in workspaces):
                raise ValueError(f"Duplicate workspace name: {workspace['name']}")
            workspaces.append((workspace, text))
        except (OSError, ValueError, yaml.YAMLError) as error:
            errors.append(str(error))

    if args.command == "list":
        print(json.dumps({"workspaces": [item[0] for item in workspaces], "errors": errors}, ensure_ascii=False, indent=2))
        return 1 if errors else 0

    if args.command == "activate":
        if errors:
            raise ValueError("\n".join(errors))
        selected = next((item for item in workspaces if item[0]["name"] == args.name), None)
        if selected is None:
            raise ValueError(f"Workspace not found: {args.name}")
        workspace, text = selected
        sessions = data / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        (sessions / f"{args.session}.json").write_text(json.dumps({"path": workspace["path"]}) + "\n", encoding="utf-8")
        print(f"Selected workspace: {workspace['name']}\nAgent working directory: {workspace['path']}\n"
              "Native session root and permissions are unchanged. Supply this working directory explicitly to shell tools "
              "and resolve workspace-relative file paths against it. No turn boundary is required.\n"
              f"Source: {workspace['path']}/AGENTS.md\n\n{text}")
        return

    payload = json.load(sys.stdin)
    session = UUID(payload["conversationId"])
    command = quote([uv, "run", "--offline", "--script", str(script), "--home", str(home)])
    context = (
            "## Workspaces\n\nWorkspaces hold instructions for a body of work, independently of skills. "
            "Select a matching workspace by description using "
            f"`{command} activate NAME --session {session}`. Read the returned live AGENTS.md and relevant linked or nested guidelines. "
            "This Antigravity adapter selects an agent-managed directory; it does not change the native session root. "
            "Use the selected directory explicitly for shell tools and resolve workspace-relative file paths against it. "
            "Host instructions and permissions remain authoritative. Save work-specific learning only with user authorization.\n\n"
            f"Refresh the catalog with `{command} list`. Register only user-authorized folders with `add PATH`; "
            f"`remove PATH` unregisters without deleting files. `{command} clear --session {session}` clears this conversation's selection.\n\n"
            + json.dumps([item[0] for item in workspaces], ensure_ascii=False, indent=2)
    )
    if errors:
        context += "\nWorkspace registration errors:\n" + "\n".join(errors)
    state = data / "sessions" / f"{session}.json"
    if state.exists():
        path = json.loads(state.read_text(encoding="utf-8"))["path"]
        if path not in entries:
            context += "\nThe previously selected workspace was unregistered. Select another workspace or clear the selection."
        elif not errors:
            workspace = next(item[0] for item in workspaces if item[0]["path"] == path)
            context += (f"\nSelected workspace: {workspace['name']}. Agent working directory: {path}. "
                       "Use it explicitly for shell tools and workspace-relative file paths. "
                       f"Read {path}/AGENTS.md if its instructions are not in context. Native session root and permissions are unchanged.")
    print(json.dumps({"injectSteps": [{"ephemeralMessage": context}]}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, yaml.YAMLError) as error:
        sys.exit(f"workspaces: {error}")
