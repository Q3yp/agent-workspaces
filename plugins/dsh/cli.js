#!/usr/bin/env node
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname } from 'node:path';
import { readCatalog, readRegistrations, readWorkspace, registryPath, workspacePath } from './registry.js';

try {
  const [command, path, ...extra] = process.argv.slice(2);
  if (command === 'list' && path === undefined) {
    const { workspaces, errors } = readCatalog();
    console.log(JSON.stringify({
      workspaces: workspaces.map(({ name, description, path }) => ({ name, description, path })), errors,
    }, null, 2));
    if (errors.length) process.exitCode = 1;
  } else if ((command === 'add' || command === 'remove') && path && extra.length === 0) {
    const root = workspacePath(path);
    const entries = readRegistrations();
    if (command === 'add') {
      const workspace = readWorkspace(root);
      for (const entry of entries) {
        if (entry !== root && readWorkspace(entry).name === workspace.name) {
          throw new Error(`Workspace name already registered: ${workspace.name}`);
        }
      }
      if (!entries.includes(root)) entries.push(root);
    } else {
      const index = entries.indexOf(root);
      if (index === -1) throw new Error(`Workspace is not registered: ${root}`);
      entries.splice(index, 1);
    }
    const file = registryPath();
    mkdirSync(dirname(file), { recursive: true });
    writeFileSync(file, JSON.stringify(entries, null, 2) + '\n', 'utf8');
    console.log(`${command === 'add' ? 'Registered' : 'Removed'}: ${root}\nFilesystem permissions are unchanged.`);
  } else {
    throw new Error('Usage: dsh-workspaces list | add PATH | remove PATH');
  }
} catch (error) {
  console.error(`workspaces: ${error.message}`);
  process.exitCode = 1;
}
