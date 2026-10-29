import { defineTool } from '@deepseek-ai/dsh-tools';
import { readCatalog } from './registry.js';

export const name = 'agent-workspaces';
export const inject = ['tools', 'systemPrompt', 'workingDirectory'];

const workspaceFields = {
  name: { type: 'string', required: true },
  description: { type: 'string', required: true },
  path: { type: 'string', required: true },
};

export function apply(ctx) {
  const tools = ctx.tools;
  const systemPrompt = ctx.systemPrompt;
  systemPrompt.section({
    name: 'agent-workspaces:guidance',
    order: 3200,
    text: 'Workspaces hold instructions for a body of work and coexist with skills. '
      + 'Select a workspace by its description when it matches the user task, then activate it with workspace_activate. '
      + 'Apply its instructions within that work\'s scope and the host instruction hierarchy. '
      + 'Read linked guidelines and relevant nested AGENTS.md files as needed. '
      + 'Save work-specific learning in the appropriate workspace instruction file only when the user authorizes it.',
  });
  systemPrompt.context({
    name: 'agent-workspaces:catalog',
    order: 300,
    interpolate: false,
    text: () => {
      const { workspaces, errors } = readCatalog();
      return '## Workspaces\n\n' + JSON.stringify(
        workspaces.map(({ name, description, path }) => ({ name, description, path })), null, 2,
      ) + (errors.length ? '\n\nRegistration errors:\n' + errors.join('\n') : '');
    },
  });
  tools.register(defineTool({
    name: 'workspace_list',
    description: 'Read the live registered workspace catalog and registration errors. Does not change the working directory.',
    parameters: {},
    output: {
      schema: {
        type: 'object', additionalProperties: false,
        properties: {
          workspaces: { type: 'array', required: true, items: {
            type: 'object', additionalProperties: false, properties: workspaceFields,
          } },
          errors: { type: 'array', required: true, items: { type: 'string' } },
        },
      },
      render: (_args, value) => [{ type: 'text', text: JSON.stringify(value, null, 2) }],
    },
    async execute(_args, exec) {
      exec.signal.throwIfAborted();
      const { workspaces, errors } = readCatalog();
      return { workspaces: workspaces.map(({ name, description, path }) => ({ name, description, path })), errors };
    },
  }));
  tools.register(defineTool({
    name: 'workspace_activate',
    description: 'Set this DSH session\'s working directory to a registered workspace and return its current AGENTS.md. '
      + 'The change applies to subsequent directory-based operations immediately. Existing processes and filesystem permissions do not change. Requires an agent session.',
    parameters: { name: { type: 'string', required: true, description: 'Workspace name from the catalog.' } },
    output: {
      schema: {
        type: 'object', additionalProperties: false,
        properties: {
          ...workspaceFields,
          source: { type: 'string', required: true },
          instructions: { type: 'string', required: true },
        },
      },
      render: (_args, value) => [{ type: 'text', text:
        `Workspace: ${value.name}\nWorking root: ${value.path}\nSource: ${value.source}\n\n${value.instructions}` }],
    },
    async execute(args, exec) {
      if (exec.agent === undefined) throw new Error('workspace_activate requires an agent session');
      exec.signal.throwIfAborted();
      const { workspaces, errors } = readCatalog();
      if (errors.length) throw new Error(errors.join('\n'));
      const workspace = workspaces.find(item => item.name === args.name);
      if (!workspace) throw new Error(`Workspace not found: ${args.name}`);
      const workingDirectory = ctx.workingDirectory;
      const path = await workingDirectory.set(exec.agent, workspace.path, exec.signal);
      return { ...workspace, path };
    },
  }));
}
