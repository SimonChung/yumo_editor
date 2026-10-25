const fs=require('node:fs');
const path=require('node:path');
const {spawnSync}=require('node:child_process');
const os=require('node:os');
const deps=process.env.YUMO_DEPS_DIR||'/opt/yumo-deps';
// Reviewers mount the candidate read-only. All generated links stay in our own
// disposable copy, so the exact same command works for review and verification.
const temp=fs.mkdtempSync(path.join(os.tmpdir(),'yumo-typecheck-'));
const frontend=path.join(temp,'frontend');
let code=1;
try {
  fs.cpSync(path.join(process.cwd(),'frontend'),frontend,{recursive:true,
    filter:source=>!['node_modules','dist'].includes(path.basename(source))});
  fs.symlinkSync(path.join(deps,'node_modules'),path.join(frontend,'node_modules'),'dir');
  const result=spawnSync(process.execPath,[path.join(deps,'node_modules/typescript/bin/tsc'),'--noEmit'],{cwd:frontend,stdio:'inherit'});
  code=result.status??1;
} finally {
  if(!path.resolve(temp).startsWith(path.resolve(os.tmpdir())+path.sep))throw new Error('Unsafe temporary path');
  fs.rmSync(temp,{recursive:true});
}
process.exit(code);
