# Workspaces for Antigravity

Discover registered workspaces and select a working directory for each conversation. Native hooks, or the T3 ACP prompt bridge, expose the catalog separately from skills. No MCP server or generated skills are used.

This is a compatibility adapter, not a conforming implementation of the specification's runtime-root activation requirement. Selection persists an agent-managed directory and returns live instructions. The agent supplies explicit shell working directories and absolute file paths. Antigravity's native session root, project identity, sandbox, and permissions remain unchanged. The standard is unchanged.

## Install

Requires Python 3.11+, uv, and Antigravity with PreInvocation hooks. From the repository root:

```sh
uv run --script plugins/antigravity/workspaces.py --home /absolute/gemini-home install
uv run --offline --script plugins/antigravity/workspaces.py --home /absolute/gemini-home add /absolute/workspace/path
```

The first command prepares the pinned dependency cache and installs the plugin in `<gemini-home>/config/plugins/workspaces`. It copies the source and generates `hooks.json` with absolute executable, script, and profile paths. Re-run it after source changes. It preserves registrations and session selections. Hooks run offline; repeat the first command if uv's dependency cache is cleared.

Without `--home`, commands use `GEMINI_HOME`, or `~/.gemini` when unset. T3 Code's managed ACP runtime uses a private Gemini home under its provider profile. Install into that profile, not the ordinary global Gemini home. Start a fresh Antigravity session after installation; already running processes may need restarting.

### T3 managed ACP 1.3.0

That build does not discover plugin hooks, ignores SessionStart handlers, and explicitly ignores `injectSteps` returned by PreInvocation hooks. Loading a hook is not sufficient to deliver its context. Use the ACP bridge:

```sh
uv run --script plugins/antigravity/workspaces.py --home /absolute/managed/gemini-home install --acp --launcher /absolute/agy-user-instructions.cjs
```

This targets the existing T3 instruction launcher used by this installation. The installer verifies its forwarding statement, makes a `.cjs.before-workspaces` backup, and inserts one call to the packaged `acp-bridge.cjs`. Existing global-instruction injection and ACP messages are preserved. The bridge adds the current catalog and selected-directory reminder to each `session/prompt`, using that request's actual session ID. Context generation failures surface as launcher errors rather than silently sending a prompt without context. The installer removes this adapter's obsolete global hook entry, preserving other hooks.

The bridge requires Node.js and the existing launcher shape; an unknown launcher fails installation instead of receiving a guessed edit. If T3 replaces the configured launcher during an update, reinstall against the replacement. Native plugin-capable hosts use the plugin's `hooks.json` without the ACP bridge.

## Registration and use

Each folder needs the name and description frontmatter defined in [the specification](../../SPEC.md). The registry contains canonical paths in `<gemini-home>/agent-workspaces/workspaces.json`. Registration is explicit and does not grant filesystem access.

```sh
uv run --offline --script plugins/antigravity/workspaces.py --home /absolute/gemini-home list
uv run --offline --script plugins/antigravity/workspaces.py --home /absolute/gemini-home activate coding --session CONVERSATION-UUID
uv run --offline --script plugins/antigravity/workspaces.py --home /absolute/gemini-home clear --session CONVERSATION-UUID
uv run --offline --script plugins/antigravity/workspaces.py --home /absolute/gemini-home remove /absolute/workspace/path
```

The catalog supplies the actual conversation UUID and activation command. Activation reads the current `AGENTS.md` and stores the selected path under `agent-workspaces/sessions/<conversation-id>.json`. Native PreInvocation hooks supply ephemeral context. In T3 ACP, the bridge supplies ordinary prompt context at each user turn, not between tool calls within a turn; the activation tool output supplies the newly selected directory immediately. Different conversations have separate selections; resuming the same conversation reuses its saved selection. There is no turn-boundary requirement or filesystem watcher. Re-activate to read edited instructions.

The catalog refreshes before each native hook invocation, each ACP user prompt, or through `list`. Missing files, malformed metadata, and duplicate names appear as catalog errors and prevent activation. Removing a registration preserves all workspace files and permissions; reminders flag a removed selection rather than continuing to endorse it. `clear` deletes only the selected conversation's state.

Directory use is prompt-directed, not enforced. A shell `cd` does not change subsequent tool processes or the host root. Host instructions loaded before selection remain in force. A runtime-root integration can replace this compatibility mechanism later without changing the workspace format.

## Validation

Validated on Windows against T3 Code's managed Antigravity ACP 1.3.0:

- Created a real ACP session with the managed profile and verified hook loading. A subsequent live check showed that the catalog was absent. Inspection of the bundled ACP hook implementation confirmed that trajectory injection is explicitly unsupported, so T3 installation now uses the prompt bridge.
- Executed the deployed hook command with conversation payloads. It returned the coding catalog and the session-specific selection command.
- Selected the real coding workspace and compared the returned instructions with its `AGENTS.md`. A subsequent hook invocation reported the selected directory, while a different conversation had no selection. Clearing removed the reminder.
- Compiled the deployed Python source successfully.

The deployed-command checks made no model requests. The initial model check exposed the ACP injection limitation described above.

After installing the bridge, a second user-authorized live check passed through the existing managed launcher on 2026-10-29. Starting in an empty scratch directory, Antigravity selected `coding` using the injected command, received its live `AGENTS.md`, and read `agent-workspaces/README.md` using the correctly resolved absolute path. The first heading matched `# Agent Workspaces`, the persisted session selection matched the coding directory, and the response correctly reported the unchanged native root. The file-read shell retained the original cwd and used an absolute path; this check does not establish that the model always sets shell cwd. The prompt completed with `end_turn`. No project files were changed by the model.

## Uninstall

Remove `<gemini-home>/config/plugins/workspaces` and restart the Antigravity process. Registry and session data remain under `<gemini-home>/agent-workspaces`; workspace folders are never deleted.

For an `--acp` installation, first remove the single line ending in `// agent-workspaces` from the instruction launcher. Keep any other launcher edits. The pre-install backup is available for comparison; do not restore it over later unrelated changes.

References: [native plugins](https://antigravity.google/docs/plugins/), [hook contracts](https://antigravity.google/docs/hooks/).

Code and configuration: [Apache 2.0](../../LICENSE-APACHE-2.0). Documentation: [CC BY 4.0](../../LICENSE-CC-BY-4.0). Fenced code examples are Apache 2.0.
