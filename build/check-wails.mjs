import { readFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const goMod = readFileSync(new URL('../go.mod', import.meta.url), 'utf8');
const expected = goMod.match(/github\.com\/wailsapp\/wails\/v3\s+(v\S+)/)?.[1];
if (!expected) throw new Error('Wails v3 version is missing from go.mod.');

const cli = spawnSync(process.execPath, [fileURLToPath(new URL('./wails.mjs', import.meta.url)), 'version'], { encoding: 'utf8' });
// Go may print download progress before the CLI writes its version to stderr.
const output = `${cli.stdout ?? ''}${cli.stderr ?? ''}`;
const versions = output.split(/\r?\n/).map(line => line.trim())
  .filter(line => /^v\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$/.test(line));
if (cli.error || cli.status !== 0 || versions.length !== 1 || versions[0] !== expected) {
  console.error(`Wails CLI must match go.mod (${expected}).`);
  console.error(output);
  console.error('Check the pinned Wails build/tools/go.mod and go.sum.');
  process.exit(1);
}

const runtime = JSON.parse(readFileSync(new URL('../frontend/node_modules/@wailsio/runtime/package.json', import.meta.url), 'utf8'));
if (`v${runtime.version}` !== expected) {
  console.error(`Wails runtime ${runtime.version} must match ${expected}. Run npm ci in frontend.`);
  process.exit(1);
}
console.log(`Wails CLI, Go module and frontend runtime match ${expected}.`);
