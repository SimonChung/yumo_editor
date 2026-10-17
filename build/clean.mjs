import { rmSync } from 'node:fs';
import { dirname, resolve, relative, isAbsolute } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const targets = process.argv.includes('--deps-only')
  ? ['frontend/node_modules']
  : ['build/bin', 'frontend/dist', 'build_windows_amd64.syso'];

for (const target of targets) {
  const absolute = resolve(root, target);
  const withinRoot = relative(root, absolute);
  if (!withinRoot || withinRoot.startsWith('..') || isAbsolute(withinRoot)) {
    throw new Error(`Refusing to clean outside the project: ${absolute}`);
  }
  console.log(`Removing ${absolute}`);
  rmSync(absolute, { recursive: true, force: true });
}
