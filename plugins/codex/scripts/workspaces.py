# /// script
# requires-python = ">=3.11"
# dependencies = ["PyYAML==6.0.3", "tomlkit==0.13.3"]
# ///

import argparse
import json
import os
from pathlib import Path
import re
import shlex
import sys

import tomlkit
import yaml


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


def main():
    parser = argparse.ArgumentParser(description="Register and activate local workspaces, independently of skills.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="Read names and descriptions from registered folders")
    commands.add_parser("context", help="Emit the session-start workspace catalog")
    commands.add_parser("add", help="Register a folder and grant future workspace-write sessions access").add_argument("path")
    commands.add_parser("remove", help="Unregister a folder and revoke only the grant added by this plugin").add_argument("path")
    commands.add_parser("activate", help="Read current workspace instructions without changing cwd").add_argument("name")
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
        print(f"Workspace: {workspace['name']}\nWorkspace root: {workspace['path']}\nWorking directory unchanged: {Path.cwd()}\n")
        print("Resolve workspace-relative paths against this root. Follow relevant nested AGENTS.md files when working in subfolders.\n")
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
        f"Activate it by running `{command} activate NAME` to read its current AGENTS.md. "
        "Activation supplies a path and instructions; it does not change the working directory or grant permissions. "
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
    except (OSError, ValueError, yaml.YAMLError) as error:
        sys.exit(f"workspaces: {error}")
