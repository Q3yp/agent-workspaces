# Agent Workspaces

A workspace is a folder that holds the instructions for a body of work. An agent discovers it by description and reads its current instructions, regardless of where the conversation started.

Workspaces coexist with skills: a workspace gives work a home and shared context; skills provide reusable capabilities. A workspace can span several repositories or contain work that is not code.

## The standard

Read the [draft specification](SPEC.md). A workspace starts with an `AGENTS.md` containing a name, a one-line description, and its instructions:

```markdown
---
name: video-production
description: Video production, including direction, assets, editing, and post-production.
---

# Video production

Keep each film in its own folder. Read direction.md before planning a film,
and post.md when editing it.
```

The catalog lists names, descriptions, and paths. Activation reads the live file; it does not copy the instructions into a plugin or change the session's working directory.

## Codex plugin

The [Codex plugin](plugins/codex/README.md) uses a session-start hook to expose a separate workspace catalog. It contains no skills and runs no MCP server.

```sh
git clone https://github.com/Q3yp/agent-workspaces.git
cd agent-workspaces
uv run --script plugins/codex/scripts/workspaces.py list
codex plugin marketplace add "$PWD"
codex plugin add workspaces@agent-workspaces
```

Review and trust its hook in `/hooks`, then start a new session. See the plugin guide for requirements, registration, write permissions, and limitations.

## Status

This is a draft standard with one reference implementation for Codex. Other agent integrations are not implemented. The plugin's registration and activation commands have been exercised locally; automatic model selection has not been evaluated.

## License

The specification and documentation are licensed under [CC BY 4.0](LICENSE-CC-BY-4.0). Implementation code, configuration files, and code examples (including fenced examples in documentation) are licensed under [Apache 2.0](LICENSE-APACHE-2.0).
