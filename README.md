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

The catalog lists names, descriptions, and paths. Activation reads the live file and updates the session's working root through the host runtime. In Codex, the update takes effect next turn: the initialization turn ends after activation, and workspace work begins in the following turn.

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

## DeepSeek Harness plugin

The [DSH plugin](plugins/dsh/README.md) is a native Cordis bundle with a live workspace catalog and activation tools. It changes the current session's working directory immediately and keeps workspaces separate from skills.

```sh
cd plugins/dsh
npm ci --ignore-scripts
cd ../..
dsh plugin --profile desktop add ./plugins/dsh
node plugins/dsh/cli.js add /absolute/workspace/path
```

Requires DSH 0.2.1-rc.2. Registration does not change filesystem permissions. See the plugin guide for packaging, other profiles, and runtime behavior.

## Antigravity compatibility adapter

The [Antigravity adapter](plugins/antigravity/README.md) exposes a workspace catalog through native hooks or T3's ACP prompt bridge and remembers an agent-managed working directory per conversation. It loads live instructions and tells the agent to use explicit paths. It does not change Antigravity's native root and therefore does not meet the standard's runtime-root activation requirement. The adapter includes installation support for T3 Code's managed ACP profile.

## Status

This is a draft standard with reference implementations for Codex and DeepSeek Harness. Registration and runtime activation have been exercised locally; automatic model selection has not been evaluated.

## License

The specification and documentation are licensed under [CC BY 4.0](LICENSE-CC-BY-4.0). Implementation code, configuration files, and code examples (including fenced examples in documentation) are licensed under [Apache 2.0](LICENSE-APACHE-2.0).
