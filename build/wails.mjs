import { spawnSync } from 'node:child_process';
import { mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { join } from 'node:path';

const root = fileURLToPath(new URL('../', import.meta.url));
const output = join(root, 'build', '.tools');
mkdirSync(output, { recursive: true });
const executable = join(output, process.platform === 'win32' ? 'wails3.exe' : 'wails3');
const build = spawnSync('go', [
  'build', '-mod=readonly', `-modfile=${join(root, 'build', 'tools', 'go.mod')}`,
  '-o', executable, 'github.com/wailsapp/wails/v3/cmd/wails3',
], { cwd: root, stdio: 'inherit' });
if (build.error) console.error(build.error.message);
if (build.error || build.status !== 0) process.exit(build.status || 1);

// Keep the caller's directory, including the Windows installer task directory.
const run = spawnSync(executable, process.argv.slice(2), { stdio: 'inherit' });
if (run.error) console.error(run.error.message);
process.exit(run.status ?? 1);
