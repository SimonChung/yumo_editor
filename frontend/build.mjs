import { execFileSync } from 'node:child_process';
import { mkdtempSync, readFileSync, renameSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseArgs } from 'node:util';

const frontend = dirname(fileURLToPath(import.meta.url));
const dist = join(frontend, 'dist');
const [mode, ...args] = process.argv.slice(2);
const esbuild = execFileSync('go', ['-C', '../build/tools', 'tool', '-n', 'esbuild'], {
  cwd: frontend, encoding: 'utf8', stdio: ['ignore', 'pipe', 'inherit'],
}).trim();
const run = flags => execFileSync(esbuild, flags, { cwd: frontend, stdio: 'inherit' });
const bundle = [
  'assets/main=src/main.tsx', '--bundle', '--format=esm', '--target=es2022',
  '--loader:.woff2=file', '--asset-names=assets/[name]-[hash]',
];

if (mode === 'build') {
  const staging = mkdtempSync(join(frontend, '.dist-'));
  try {
    const meta = join(staging, 'meta.json');
    run([...bundle, '--minify', '--entry-names=[dir]/[name]-[hash]', `--outdir=${staging}`, `--metafile=${meta}`]);
    const { outputs } = JSON.parse(readFileSync(meta, 'utf8'));
    const [js, info] = Object.entries(outputs).find(([, output]) => output.entryPoint === 'src/main.tsx');
    const assetURL = path => './' + relative(staging, join(frontend, path)).replaceAll('\\', '/');
    const html = readFileSync(join(frontend, 'index.html'), 'utf8')
      .replace('./assets/main.js', assetURL(js)).replace('./assets/main.css', assetURL(info.cssBundle));
    writeFileSync(join(staging, 'index.html'), html);
    rmSync(meta);
    rmSync(dist, { recursive: true, force: true });
    renameSync(staging, dist);
  } finally {
    rmSync(staging, { recursive: true, force: true });
  }
} else if (mode === 'dev' || mode === 'preview') {
  const { values } = parseArgs({
    args: args.map((arg, i) => arg === '--host' && (!args[i + 1] || args[i + 1].startsWith('-')) ? '--host=0.0.0.0' : arg),
    options: {
      host: { type: 'string', default: '127.0.0.1' },
      port: { type: 'string' },
      strictPort: { type: 'boolean' },
    },
  });
  const port = values.port ?? (mode === 'dev' ? process.env.WAILS_VITE_PORT || '5173' : '4173');
  const serve = `--serve=${values.host}:${port}`;
  if (mode === 'preview') {
    readFileSync(join(dist, 'index.html'));
    run([serve, `--servedir=${dist}`]);
  } else {
    // A WebView can buffer the Wails asset proxy's event stream. Connect
    // directly to the development server for reload events in desktop mode.
    const desktopURL = process.env.FRONTEND_DEVSERVER_URL;
    const events = desktopURL ? new URL('/esbuild', desktopURL).href : '/esbuild';
    const desktopOrigin = process.platform === 'win32' ? 'http://wails.localhost' : 'wails://localhost';
    const cors = desktopURL ? [`--cors-origin=${desktopOrigin}:${port}`] : [];
    const reload = `new EventSource(${JSON.stringify(events)}).addEventListener('change', () => {
      if (!document.querySelector('.tab-item.dirty')) location.reload();
    });`;
    run([
      ...bundle, 'index=index.html', '--loader:.html=copy', '--entry-names=[dir]/[name]', '--sourcemap',
      `--banner:js=${reload}`, '--outdir=.esbuild-dev', '--watch=forever', ...cors, serve,
    ]);
  }
} else {
  throw new Error('Expected build, dev or preview');
}
