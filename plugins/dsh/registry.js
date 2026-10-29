import { existsSync, readFileSync, realpathSync } from 'node:fs';
import { homedir } from 'node:os';
import { isAbsolute, join, resolve } from 'node:path';
import { parse } from 'yaml';

export function registryPath() {
  return join(resolve(process.env.DSH_HOME || join(homedir(), '.dsh')), 'workspaces.json');
}

export function workspacePath(path) {
  const expanded = path === '~' ? homedir() : /^~[/\\]/.test(path) ? join(homedir(), path.slice(2)) : path;
  const absolute = resolve(expanded);
  return existsSync(absolute) ? realpathSync.native(absolute) : absolute;
}

export function readWorkspace(path) {
  const root = realpathSync.native(path);
  const source = join(root, 'AGENTS.md');
  const instructions = readFileSync(source, 'utf8');
  const frontmatter = /^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/.exec(instructions);
  if (!frontmatter) throw new Error(`${source}: add YAML frontmatter with name and description`);
  const metadata = parse(frontmatter[1]);
  if (metadata === null || typeof metadata !== 'object' || Array.isArray(metadata)) {
    throw new Error(`${source}: frontmatter must be a mapping`);
  }
  if (typeof metadata.name !== 'string' || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(metadata.name)) {
    throw new Error(`${source}: name must use lowercase words separated by hyphens`);
  }
  if (typeof metadata.description !== 'string' || !metadata.description.trim() || /[\r\n]/.test(metadata.description)) {
    throw new Error(`${source}: description must be one nonempty line`);
  }
  return { name: metadata.name, description: metadata.description.trim(), path: root, source, instructions };
}

export function readRegistrations() {
  const file = registryPath();
  if (!existsSync(file)) return [];
  let entries;
  try {
    entries = JSON.parse(readFileSync(file, 'utf8'));
  } catch (error) {
    throw new Error(`${file}: ${error.message}`, { cause: error });
  }
  if (!Array.isArray(entries) || entries.some(entry => typeof entry !== 'string' || !isAbsolute(entry))) {
    throw new Error(`${file}: expected an array of absolute workspace paths`);
  }
  return entries;
}

export function readCatalog() {
  const workspaces = [];
  const errors = [];
  for (const path of readRegistrations()) {
    try {
      const workspace = readWorkspace(path);
      if (workspaces.some(item => item.name === workspace.name)) {
        throw new Error(`Duplicate workspace name: ${workspace.name}`);
      }
      workspaces.push(workspace);
    } catch (error) {
      errors.push(String(error));
    }
  }
  return { workspaces, errors };
}
