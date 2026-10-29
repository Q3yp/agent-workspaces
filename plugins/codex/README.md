# Workspaces for Codex

Discover local bodies of work from any session, then read their current instructions without changing the session's working directory. Workspaces coexist with skills. This plugin contains no skills and runs no MCP server.

## Install

Requires Codex with plugin hooks, Python 3.11+, and `uv` on the hook process's PATH. From the repository root:

```sh
uv run --script plugins/codex/scripts/workspaces.py list
codex plugin marketplace add "$PWD"
codex plugin add workspaces@agent-workspaces
```

The first command prepares the pinned Python dependencies in uv's cache. Hooks run offline; if that cache is cleared, run the first command again. Review and trust the plugin's SessionStart hook in Codex's `/hooks`, then start a new session. `features.hooks` must be enabled. Plugin installation does not itself grant hook trust.

## Register a workspace

Add frontmatter to the folder's top-level `AGENTS.md`:

```yaml
---
name: video-production
description: Local video production, including direction, assets, shots and post-production.
---
```

Keep its instructions below the frontmatter, then run:

```sh
uv run --offline --script plugins/codex/scripts/workspaces.py add /absolute/workspace/path
```

Registration stores the canonical folder path in `$CODEX_HOME/workspaces.json` (default `~/.codex/workspaces.json`). Names and descriptions come from `AGENTS.md`; there is no generated skill or cached instruction copy. Names must be unique lowercase hyphenated identifiers. Descriptions must be a single nonempty line.

Adding a workspace appends its path to `sandbox_workspace_write.writable_roots` in the user Codex configuration. This applies to future workspace-write sessions, including sessions where that workspace is inactive. It does not change the sandbox mode or override host/managed restrictions. Existing settings and comments are preserved.

```sh
uv run --offline --script plugins/codex/scripts/workspaces.py list
uv run --offline --script plugins/codex/scripts/workspaces.py activate video-production
uv run --offline --script plugins/codex/scripts/workspaces.py remove /absolute/workspace/path
```

Activation returns the current `AGENTS.md`, source path, and workspace root. It does not persist an active-workspace flag or change directories. The agent keeps the selected workspace in the conversation and reads relevant linked and nested instructions. Removal unregisters the folder and removes its exact write-root entry only if this plugin added it; it never deletes workspace files.

## Behavior and limits

- A plugin SessionStart hook injects a distinct workspace catalog on startup, resume, and after compaction. The agent chooses by description and reads the live file. This is prompt-directed selection, not a new built-in Codex workspace type or UI.
- No workspace enters the skill catalog; existing skills remain available independently.
- The catalog refreshes at session-start events or through `list`. Activation always reads current instructions. There is no automatic mid-turn file-change notification.
- Registration is explicit. No default folder is scanned, moved, or automatically granted write access.
- Workspace instructions cannot erase native instructions already loaded from the session's starting directory. They apply to their body of work within the host's instruction hierarchy.
- Work-specific learning belongs with the work, but saving it still requires the user's authorization. The plugin does not change Codex's own memory policy.
- Existing folders need frontmatter before registration. Installation does not register or edit them.

References: [plugin packaging](https://developers.openai.com/plugins/build/plugins), [hooks and trust](https://learn.chatgpt.com/docs/hooks), [write-root configuration](https://learn.chatgpt.com/docs/config-file/config-reference).

## Validation

On Codex CLI 0.164.0 on macOS:

- Installed through `codex plugin marketplace add` and `codex plugin add`.
- Queried the running app-server's `hooks/list`: plugin hook discovered and enabled, with no warnings or errors; trust status was `untrusted`.
- Ran the installed script offline against a temporary copy of video-production instructions. Registration was idempotent; the catalog showed its metadata; activation returned the original instructions plus a subsequent live edit; cwd stayed unchanged. Existing configuration and write roots survived registration and removal.
- Parsed the Python source successfully.

No model request was made. Automatic workspace selection and context delivery after hook trust have not been exercised in a live conversation.

## Uninstall

Remove registered workspaces first if their plugin-added write grants should also be revoked. Then:

```sh
codex plugin remove workspaces@agent-workspaces
codex plugin marketplace remove agent-workspaces
```

The source directory and workspace files remain in place.

## License

Code and configuration: [Apache 2.0](../../LICENSE-APACHE-2.0). Documentation: [CC BY 4.0](../../LICENSE-CC-BY-4.0). Fenced code examples are Apache 2.0.
