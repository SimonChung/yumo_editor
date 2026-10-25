import { readFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';

const goMod = readFileSync(new URL('../go.mod', import.meta.url), 'utf8');
const expected = goMod.match(/github\.com\/wailsapp\/wails\/v3\s+(v\S+)/)?.[1];
if (!expected) throw new Error('Wails v3 version is missing from go.mod.');

const cli = spawnSync('wails3', ['version'], { encoding: 'utf8' });
// The Wails CLI writes its version to stderr.
const actual = `${cli.stdout ?? ''}${cli.stderr ?? ''}`.trim();
if (cli.error || cli.status !== 0 || actual !== expected) {
  console.error(`Wails CLI must match go.mod (${expected}).`);
  console.error(`Install: go install github.com/wailsapp/wails/v3/cmd/wails3@${expected}`);
  process.exit(1);
}

const runtime = JSON.parse(readFileSync(new URL('../frontend/node_modules/@wailsio/runtime/package.json', import.meta.url), 'utf8'));
if (`v${runtime.version}` !== expected) {
  console.error(`Wails runtime ${runtime.version} must match ${expected}. Run npm ci in frontend.`);
  process.exit(1);
}
console.log(`Wails CLI, Go module and frontend runtime match ${expected}.`);
