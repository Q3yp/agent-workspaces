# Agent Workspaces specification

Status: draft

## Purpose

A workspace gives a body of work a stable home for instructions and shared knowledge. An agent can discover and activate it from a session started elsewhere. The work may span repositories, documents, media, or other files.

Workspaces are separate from skills. Registering a workspace does not register a skill, and activating one does not replace the available skills.

## Workspace structure

A workspace is a folder with a top-level `AGENTS.md`. That file contains YAML frontmatter with:

- `name`: a unique catalog identifier made of lowercase letters or digits, with hyphens between words.
- `description`: a nonempty, one-line description of the work.

These fields are the source of truth for the workspace's identity and description. Instructions follow the frontmatter. Additional metadata fields are not defined by this draft.

The top-level instructions hold conventions shared across the work and link to more specific guideline files. Individual pieces of work can live in subfolders with their own `AGENTS.md`. A repository can occupy one of those subfolders.

## Registration and discovery

Registration records the workspace folder's absolute path. An implementation reads its name and description from the live `AGENTS.md`, rather than maintaining independent editable copies. Names must be unique within the catalog.

Sessions receive a catalog of registered workspace names, descriptions, and paths. The agent uses those descriptions to select the workspace relevant to the user's request. Unrelated workspace instructions need not be loaded.

An implementation must document when it refreshes the catalog and how it reports missing folders, malformed metadata, and duplicate names. This draft does not prescribe a default directory or automatic registration by scanning.

## Activation

Activation reads the selected workspace's current `AGENTS.md` and sets its absolute path as the session's working root through the host runtime. Workspace-relative references resolve against that root. Returning a path or asking the agent to supply a working directory is not a runtime root change.

Activation does not require a new conversation and does not itself grant filesystem access. A host may apply the root change at the next turn boundary. In that case, activation must state that the current turn still uses its original directory and that workspace work begins in the next turn. The initialization turn ends after activation. A tool call is not a turn boundary.

An implementation must receive the host's acceptance before reporting that the root update was accepted. If the host is unreachable or rejects the update, activation fails rather than presenting instructions alone as successful activation. Integrations must document any host overrides that can replace the root on later turns. The agent reads linked guidelines and relevant nested `AGENTS.md` files as needed.

Instructions remain in the workspace folder. Editing them takes effect on the next read without rebuilding or reinstalling the integration. Automatic file-change notification during a turn is optional and must not be implied when unavailable.

The host's instruction hierarchy still applies. Activation does not erase native instructions already loaded from the session's starting directory. Nested instructions refine the work they cover within that hierarchy.

## Permissions

Registration requires the user's authorization to add the folder. Where supported, registration also configures the host's allowed write directories for subsequent sessions. The implementation must explain that this grant may apply even when the workspace is inactive.

Host sandbox settings and managed restrictions remain authoritative. Registration must not silently disable sandboxing or claim access that the host has not granted. Implementations must distinguish catalog registration from effective filesystem access.

Unregistration removes the catalog entry without deleting workspace files. Implementations that revoke write grants must preserve grants that existed independently of registration.

## Shared knowledge

Work-specific learning belongs in the most general applicable workspace file: the top-level `AGENTS.md`, a linked guideline, or a subfolder's instructions. This makes it available to agents that later activate the same workspace.

Saving a correction still follows the user's authorization and the host's memory policy. The workspace format does not override either or reconfigure the agent's own memory system.

## Integration and migration

An integration exposes workspaces alongside skills, using host-supported context or tool mechanisms. It must not represent each workspace as a skill.

Existing folders can be registered in place after adding the required frontmatter. Sessions started inside a workspace may load its instructions natively; sessions started elsewhere read the same source through activation. Moving the folder is unnecessary.

The [Codex reference implementation](plugins/codex/README.md) provides a session-start catalog and live activation command. The [DeepSeek Harness implementation](plugins/dsh/README.md) refreshes its catalog on prompt assembly and activates through the native per-session working-directory service. Other hosts may implement these behaviors differently.

## Open questions

- Whether to standardize a default location for new workspaces.
- How to describe linked repositories outside the workspace folder.
- How hosts should expose and refresh workspace selection during long conversations.
- Whether automatic discovery and activation of several workspaces need additional conventions.
