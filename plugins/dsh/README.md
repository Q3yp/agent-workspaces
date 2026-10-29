# Workspaces for DeepSeek Harness

Discover registered bodies of work, activate one in the current DSH session, and read its live instructions. This native Cordis bundle adds a workspace catalog and two tools alongside the existing skills. It runs no MCP server and creates no skills.

## Install

Requires Node.js 22.19+ and DSH **0.2.1-rc.2**, the release used for runtime validation. The package pins its DSH compatibility to that release. The profile must provide `tools`, `systemPrompt`, and `workingDirectory`, as the standard base-backed profiles do. This integration uses local host folders.

From this repository's root:

```sh
cd plugins/dsh
npm ci --ignore-scripts
npm pack
cd ../..
dsh plugin --profile desktop add ./plugins/dsh
```

If DSH is not on PATH, replace `dsh` with `npx @deepseek-ai/dsh@0.2.1-rc.2`. Use `web` or another profile name instead of `desktop` for that host. Restart the profile if installation reports `restart-required`.

The source is executable ES modules; no transpilation step is needed. `npm pack` builds `dsh-agent-workspaces-0.1.0.tgz`, which can also be passed to `dsh plugin ... add`. DSH packages are host-provided peers. The local dependency lock and Zod override keep the development installation on a patched Zod release; a consuming DSH installation owns its own host dependencies.

## Register a workspace

Give its top-level `AGENTS.md` the metadata defined in [the specification](../../SPEC.md):

```markdown
---
name: video-production
description: Video direction, assets, editing, and post-production.
---

Read direction.md before planning a film.
```

Run these commands from the repository root:

```sh
node plugins/dsh/cli.js add /absolute/workspace/path
node plugins/dsh/cli.js list
node plugins/dsh/cli.js remove /absolute/workspace/path
```

Quote paths containing spaces. The packaged CLI is also exposed as `dsh-workspaces` when installed on PATH. Registration stores canonical absolute folder paths in `$DSH_HOME/workspaces.json`, defaulting to `~/.dsh/workspaces.json`. Metadata and instructions remain in each workspace's live file. Register only folders the user authorizes. This registry is separate from Codex's registry.

Registration does **not** grant filesystem permissions or change the sandbox. Configure any needed write roots through the host's permission settings. Activation changes the working directory, not those grants. Removal unregisters a folder without deleting its files or changing permissions.

## Session behavior

The agent receives a separate workspace catalog as dynamic context, refreshed on prompt assembly. `workspace_list` also refreshes it. Names, descriptions, and paths are listed; full instructions are returned only on activation.

`workspace_activate({"name":"video-production"})` reads the live file, awaits DSH's `workingDirectory.set`, and returns the accepted root and instructions. Subsequent directory-based tools use that root immediately in the same conversation. No next-turn boundary is required. Other sessions and existing processes retain their own working directories.

The native service records directory changes in the session log and restores them on replay. The session's original project identity and UI grouping remain unchanged. If the selected directory disappears, DSH can restore the original project directory. A later directory change by the user or another tool supersedes activation.

Workspace instructions apply within the host's instruction hierarchy. Follow linked guidelines and relevant nested instructions as needed. Activating again reads edits immediately. There is no plugin file watcher; any native instruction watching is supplied by DSH. Learning is saved only with user authorization.

Malformed workspace metadata, missing files, and duplicate names appear as catalog errors. Activation fails while the catalog contains errors, so a duplicate name cannot select an arbitrary workspace. A malformed registry fails the read with its source path. Repair or unregister invalid entries. A rejected runtime directory change is a tool error, never an instruction-only activation success.

## Validation

Validated on Windows with Node.js 24.22.1 and DSH packages 0.2.1-rc.2, using DSH's production AgentLoop, tool registry, local filesystem, system-prompt registry, and working-directory service:

- CLI registration is idempotent and removal preserves workspace files.
- Prompt assembly includes the catalog independently of skills.
- Activation changes the calling session's root; a subsequent native `read` resolves a relative file in that workspace.
- A sibling session retains its original directory, and session-log replay restores the selected root.
- Activation returns live instruction edits; unknown names and malformed metadata fail.

These checks made no model requests and do not measure automatic model selection.

The integration follows DSH's [bundle packaging](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/user/develop/basic/publish.md) and [native working-directory service](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/session/working-directory/src/index.ts).

## Uninstall

```sh
dsh plugin --profile desktop remove dsh-agent-workspaces
```

Registered paths and workspace files remain in place. Use the registration CLI to remove entries if desired.

Code and configuration: [Apache 2.0](../../LICENSE-APACHE-2.0). Documentation: [CC BY 4.0](../../LICENSE-CC-BY-4.0). Fenced code examples are Apache 2.0.
