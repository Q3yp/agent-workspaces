const { readFileSync } = require('node:fs');
const { join } = require('node:path');
const { spawnSync } = require('node:child_process');

module.exports = function injectWorkspaceContext(message) {
  if (message.method !== 'session/prompt') return message;
  const [command, ...args] = JSON.parse(readFileSync(join(__dirname, 'acp-command.json'), 'utf8'));
  const result = spawnSync(command, [...args, 'context'], {
    input: JSON.stringify({ conversationId: message.params.sessionId }),
    encoding: 'utf8',
    windowsHide: true,
    timeout: 30000,
  });
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error(`Workspace context failed: ${result.stderr}`);
  const context = JSON.parse(result.stdout);
  message.params.prompt.unshift({
    type: 'text',
    text: context.injectSteps.map(step => step.ephemeralMessage).join('\n\n'),
  });
  return message;
};
