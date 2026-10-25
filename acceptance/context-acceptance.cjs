/* Independent acceptance: real React components, mocked native I/O boundary.
 * Native Explorer/OLE behavior and Go builds are separately verified on Windows.
 * Public bridge contract: Events.On('files-dropped', event => event.data.files).
 */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const {createRequire} = require('node:module');
const deps = process.env.YUMO_DEPS_DIR || '/opt/yumo-deps';
const req = createRequire(path.join(deps, 'package.json'));
const {JSDOM} = req('jsdom');
const {buildSync} = req('esbuild');
const {build} = req('esbuild');
const rootDir = process.cwd();
const dom = new JSDOM('<!doctype html><html><body><div id="root"></div></body></html>', {url:'http://localhost'});
for (const name of ['window','document','navigator','Element','Document','DocumentFragment','NodeFilter','HTMLElement','HTMLTextAreaElement','Event','MouseEvent','KeyboardEvent','Node']) {
  Object.defineProperty(globalThis,name,{value:dom.window[name],configurable:true,writable:true});
}
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
window.HTMLElement.prototype.scrollTo = function() {};
const React = req('react');
const {act} = React;
const {createRoot} = req('react-dom/client');
const state = {listeners:new Map(),files:new Map(),reads:[],saves:[],alerts:[],selected:'',savePath:'',delay:0,startup:[],startupError:null};
globalThis.__dropBoundary = {
  Events: {
    On(name,callback) {const set=state.listeners.get(name)||new Set();set.add(callback);state.listeners.set(name,set);return ()=>set.delete(callback);},
    Off(name) {state.listeners.delete(name);},
  },
  async GetStartupFiles() {if(state.startupError)throw state.startupError;return [...state.startup];},
  async OpenFile(p) {state.reads.push(p);if(state.delay)await new Promise(r=>setTimeout(r,state.delay));const value=state.files.get(p);if(value instanceof Error)throw value;if(value===undefined)throw new Error('missing '+p);return value;},
  async SaveFile(...args) {state.saves.push(args);},
  async SelectFile() {return state.selected;},
  async SelectSaveFile() {return state.savePath;},
};
window.alert = globalThis.alert = text=>state.alerts.push(String(text));
window.confirm = globalThis.confirm = ()=>true;
let App, renderer;
const P='C:\\拖放驗收\\中文 空白.txt';
function tabs(){return [...document.querySelectorAll('.tab-item')];}
function named(name){return tabs().filter(t=>t.querySelector('.tab-name')?.textContent===name);}
function editor(){return document.querySelector('textarea');}
function emit(paths){for(const f of state.listeners.get('files-dropped')||[])f({name:'files-dropped',data:{files:paths}});}
async function settle(fn){await act(async()=>{if(fn)fn();await new Promise(r=>setTimeout(r,70));});}
function put(p,content='hello',encoding='UTF-8'){state.files.set(p,{content,encoding});}
async function mount(strict=false,startup=[],files={}){
  if(renderer)await act(()=>renderer.unmount());
  Object.assign(state,{listeners:new Map(),files:new Map(),reads:[],saves:[],alerts:[],selected:'',savePath:'',delay:0,startup,startupError:null});
  for(const [name,value] of Object.entries(files))state.files.set(name,value);
  document.body.innerHTML='<div id="root"></div>';
  renderer=createRoot(document.querySelector('#root'));
  await act(()=>renderer.render(strict?React.createElement(React.StrictMode,null,React.createElement(App)):React.createElement(App)));
}
async function drop(paths){await settle(()=>emit(paths));}
async function key(key,shift=false){await settle(()=>window.dispatchEvent(new KeyboardEvent('keydown',{key,ctrlKey:true,shiftKey:shift,bubbles:true,cancelable:true})));}
async function edit(value){const el=editor();assert.ok(el,'editor textarea exists');await settle(()=>{Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set.call(el,value);el.dispatchEvent(new Event('input',{bubbles:true}));});}
async function choose(name){assert.equal(named(name).length,1);await settle(()=>named(name)[0].dispatchEvent(new MouseEvent('click',{bubbles:true})));}
const cases=[];
function test(name,fn){cases.push([name,fn]);}

test('startup empty arguments leave blank document',async()=>{
  await mount();await settle();assert.equal(state.reads.length,0);assert.equal(tabs().length,1);
});
test('startup Chinese spaced path opens actual React tab and content',async()=>{
  await mount(false,[P],{[P]:{content:'啟動檔案內容',encoding:'UTF-8'}});await settle();
  assert.equal(named('中文 空白.txt').length,1);assert.equal(editor()?.value,'啟動檔案內容');assert.deepEqual(state.reads,[P]);
});
test('startup duplicates and StrictMode do not reread or duplicate tabs',async()=>{
  await mount(true,[P,P],{[P]:{content:'once',encoding:'UTF-8'}});await settle();
  assert.equal(named('中文 空白.txt').length,1);assert.equal(state.reads.filter(p=>p===P).length,1);
});
test('startup missing file reports error and continues to valid file',async()=>{
  await mount(false,['C:\\missing.txt',P],{[P]:{content:'survives',encoding:'UTF-8'}});await settle();
  assert.equal(editor()?.value,'survives');assert.ok(state.alerts.join(' ').includes('missing.txt'));
});
test('startup file saves to original path and encoding',async()=>{
  await mount(false,[P],{[P]:{content:'繁體',encoding:'Big5'}});await settle();await edit('啟動後修改');await key('s');
  assert.deepEqual(state.saves.at(-1),[P,'啟動後修改','Big5']);
});
test('startup followed by native drop preserves dirty content',async()=>{
  await mount(false,[P],{[P]:{content:'original',encoding:'UTF-8'}});await settle();await edit('unsaved');
  put(P,'different disk');await drop([P]);assert.equal(editor()?.value,'unsaved');assert.equal(state.reads.length,1);
});
test('installer source registers quoted command and uninstall cleanup',async()=>{
  const nsi=fs.readFileSync(path.join(rootDir,'build/windows/installer/project.nsi'),'utf8');
  assert.equal(nsi.charCodeAt(0),0xFEFF,'NSIS source needs a UTF-8 BOM for the existing Windows ACP invocation');
  assert.match(nsi,/WriteRegStr\s+SHELL_CONTEXT\s+"Software\\Classes\\\*\\shell\\[^"\\]+"\s+""\s+"以 YuMo Editor 編輯"/);
  assert.match(nsi,/WriteRegStr\s+SHELL_CONTEXT\s+"Software\\Classes\\\*\\shell\\[^"\\]+\\command"[^\n]+%1/);
  const command=nsi.split(/\r?\n/).find(l=>/WriteRegStr.*\\command.*%1/.test(l));
  assert.ok(command.includes('$\\"$INSTDIR\\${PRODUCT_EXECUTABLE}$\\" $\\"%1$\\"'),'quote executable and file argument');
  assert.match(nsi.split('Section "uninstall"')[1],/DeleteRegKey\s+SHELL_CONTEXT\s+"Software\\Classes\\\*\\shell\\[^"\\]+"/);
});

test('native window enables OS drop and forwards real DroppedFiles',async()=>{
  const sources=fs.readdirSync(rootDir).filter(n=>n.endsWith('.go')&&!n.endsWith('_test.go')).map(n=>fs.readFileSync(n,'utf8')).join('\n');
  assert.match(sources,/EnableFileDrop\s*:\s*true/);
  assert.match(sources,/OnWindowEvent\s*\(\s*events\.Common\.WindowFilesDropped/);
  assert.match(sources,/\.DroppedFiles\(\)/);
  assert.match(sources,/\.Event\.Emit\(\s*"files-dropped"/);
});
test('rendered editing area is a native drop target with one live subscription',async()=>{
  await mount();assert.ok(document.querySelector('[data-file-drop-target]'));
  assert.equal(state.listeners.get('files-dropped')?.size,1);
});
test('Chinese path with spaces opens actual content and replaces pristine placeholder',async()=>{
  await mount();put(P,'你好，拖放');await drop([P]);assert.equal(named('中文 空白.txt').length,1);assert.equal(editor()?.value,'你好，拖放');assert.equal(tabs().length,1);assert.ok(document.body.textContent.includes(P));
});
test('multiple files preserve content, unique tabs, and last successful selection',async()=>{
  await mount();put(P,'one');put('C:\\a\\two.txt','two');put('C:\\b\\two.txt','another');await drop([P,'C:\\a\\two.txt','C:\\b\\two.txt']);
  assert.equal(tabs().length,3);assert.equal(named('two.txt').length,2);assert.equal(editor()?.value,'another');
});
test('duplicate path within one batch reads and opens once',async()=>{
  await mount();put(P);await drop([P,P,P]);assert.equal(named('中文 空白.txt').length,1);assert.equal(state.reads.filter(p=>p===P).length,1);
});
test('repeated drop selects dirty tab without disk reread or overwrite',async()=>{
  await mount();put(P,'disk');await drop([P]);await edit('unsaved edit');assert.ok(named('中文 空白.txt')[0].classList.contains('dirty'));
  put(P,'changed disk');await drop([P]);assert.equal(editor()?.value,'unsaved edit');assert.equal(named('中文 空白.txt').length,1);assert.equal(state.reads.length,1);
});
test('fast overlapping native events cannot create duplicate tabs',async()=>{
  await mount();put(P,'slow');put('C:\\other.txt','other');state.delay=12;
  await settle(()=>{emit([P]);emit([P,'C:\\other.txt']);});
  assert.equal(named('中文 空白.txt').length,1);assert.equal(named('other.txt').length,1);assert.equal(state.reads.filter(p=>p===P).length,1);
});
test('failed path does not prevent subsequent valid file and reports error',async()=>{
  await mount();state.files.set('C:\\missing.txt',new Error('無法讀取 missing.txt'));put(P,'survives');await drop(['C:\\missing.txt',P]);
  assert.equal(editor()?.value,'survives');assert.equal(named('missing.txt').length,0);assert.ok((state.alerts.join(' ')+' '+document.body.textContent).includes('missing.txt'));
});
test('directory and binary results do not create tabs or abort rest of batch',async()=>{
  await mount();state.files.set('C:\\folder',new Error('directory'));state.files.set('C:\\binary.bin',null);put(P,'valid');await drop(['C:\\folder','C:\\binary.bin',P]);assert.equal(tabs().length,1);assert.equal(editor()?.value,'valid');
});
test('empty drop leaves existing dirty document untouched',async()=>{
  await mount();put(P);await drop([P]);await edit('keep');await drop([]);assert.equal(editor()?.value,'keep');assert.equal(tabs().length,1);
});
test('dragged document saves to original path with detected encoding',async()=>{
  await mount();put(P,'繁體','Big5');await drop([P]);await edit('修改後');await key('s');assert.deepEqual(state.saves.at(-1),[P,'修改後','Big5']);assert.ok(!named('中文 空白.txt')[0].classList.contains('dirty'));
});
test('dialog open and drop share deduplication and preserve edits',async()=>{
  await mount();put(P,'original');state.selected=P;await key('o');await edit('from menu');await drop([P]);assert.equal(tabs().length,1);assert.equal(editor()?.value,'from menu');state.selected=P;await key('o');assert.equal(editor()?.value,'from menu');assert.equal(state.reads.length,1);
});
test('Markdown and SVG use their existing editing and preview routes',async()=>{
  await mount();put('C:\\note.md','# dropped markdown');put('C:\\image.svg','<svg xmlns="http://www.w3.org/2000/svg"><text>drop</text></svg>');await drop(['C:\\note.md']);assert.equal(editor()?.value,'# dropped markdown');assert.ok(document.querySelector('.markdown-workspace'));
  await drop(['C:\\image.svg']);assert.ok(document.querySelector('iframe[sandbox]'));assert.ok(editor()?.value.includes('<svg'));
});
test('dirty untitled document is retained when a file is dropped',async()=>{
  await mount();await edit('unsaved untitled');put(P);await drop([P]);assert.equal(tabs().length,2);await choose('Untitled-1');assert.equal(editor()?.value,'unsaved untitled');
});
test('closing a dropped tab permits reopening current disk contents',async()=>{
  await mount();put(P,'old');await drop([P]);await key('w');put(P,'fresh');await drop([P]);assert.equal(editor()?.value,'fresh');assert.equal(named('中文 空白.txt').length,1);
});
test('subscription cleanup survives React StrictMode mount and unmount',async()=>{
  await mount(true);assert.equal(state.listeners.get('files-dropped')?.size,1);await act(()=>renderer.unmount());renderer=null;assert.equal(state.listeners.get('files-dropped')?.size||0,0);
});

(async()=>{
  const compiled=await build({entryPoints:[path.join(rootDir,'frontend/src/App.tsx')],bundle:true,write:false,format:'cjs',platform:'node',jsx:'automatic',nodePaths:[path.join(deps,'node_modules')],logLevel:'silent',plugins:[{
    name:'native-boundary',setup(b){
      b.onResolve({filter:/^@wailsio\/runtime$/},()=>({path:'runtime',namespace:'native'}));
      b.onResolve({filter:/bindings\/tw\.ybak\/yumo\/app(?:\.js)?$/},()=>({path:'bindings',namespace:'native'}));
      b.onLoad({filter:/.*/,namespace:'native'},args=>({contents:args.path==='runtime'?'export const Events=globalThis.__dropBoundary.Events;':'export const {GetStartupFiles,OpenFile,SaveFile,SelectFile,SelectSaveFile}=globalThis.__dropBoundary;'}));
      b.onResolve({filter:/\.css$/},()=>({path:'css',namespace:'empty'}));b.onLoad({filter:/.*/,namespace:'empty'},()=>({contents:''}));
      b.onResolve({filter:/^(react|react-dom)(\/.*)?$/},args=>({path:req.resolve(args.path),external:true}));
    }
  }]});
  const output=path.join(os.tmpdir(),'yumo-app-'+process.pid+'.cjs');fs.writeFileSync(output,compiled.outputFiles[0].text);App=require(output).default;
  let failures=0;
  for(const [name,fn] of cases){try{await fn();console.log('PASS '+name);}catch(e){failures++;console.log('FAIL '+name+'\n'+String(e.stack));}}
  if(renderer)await act(()=>renderer.unmount());dom.window.close();fs.unlinkSync(output);
  console.log(JSON.stringify({total:cases.length,passed:cases.length-failures,failed:failures}));process.exitCode=failures?1:0;
})().catch(e=>{console.error(e);process.exitCode=1;dom.window.close();});
