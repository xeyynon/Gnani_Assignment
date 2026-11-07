// ui_check/drive.mjs: drive a real page through a list of steps in headless Chrome and say which ones hold.
//   node --experimental-websocket scripts/ui_check/drive.mjs <url> <steps.mjs> [width] [height] [dark|light] [basicAuthBase64]
// steps.mjs exports  steps = [{ name, js, expect?, shot? }].  js is an async snippet run in the page (use return);
// expect is compared as JSON with what it returns (PASS or FAIL);  shot is a file to save a screenshot to after the step. Overflow is
// checked after every step that takes a shot. Exit code is 1 if anything failed. Run each flow on a FRESH server: a flow
// that creates things is not safe to run twice against the same one. CHROME_FLAGS adds browser flags, for example
// '--use-fake-ui-for-media-stream --use-fake-device-for-media-stream' so a page can open a fake microphone. Wait until the server answers before starting.
import { existsSync } from 'node:fs';
function chromePath() {                     // CHROME=/path/to/chrome overrides; otherwise the usual places
  const candidates = [process.env.CHROME, 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe', '/usr/bin/google-chrome', '/usr/bin/chromium',
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'];
  const found = candidates.find(c => c && existsSync(c));
  if (!found) throw new Error('Chrome not found. Set CHROME to its path.');
  return found;
}
import { spawn } from 'node:child_process';
import { writeFileSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';

const [url, stepsFile, w = '1280', hgt = '900', scheme = 'light', auth = ''] = process.argv.slice(2);
const { steps } = await import(pathToFileURL(stepsFile).href);
const port = 9800 + Math.floor(Math.random() * 150);
const chrome = spawn(chromePath(),
  ['--headless=new', '--disable-gpu', ...(process.env.CHROME_FLAGS ? process.env.CHROME_FLAGS.split(' ') : []), `--remote-debugging-port=${port}`, `--user-data-dir=${mkdtempSync(join(tmpdir(), 'cdp'))}`, 'about:blank'], { stdio: 'ignore' });
const sleep = ms => new Promise(r => setTimeout(r, ms));
let target;
for (let i = 0; i < 50 && !target; i++) { await sleep(200); try { target = (await (await fetch(`http://127.0.0.1:${port}/json`)).json()).find(t => t.type === 'page'); } catch {} }
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise(r => ws.onopen = r);
let id = 0; const waits = {};
ws.onmessage = e => { const m = JSON.parse(e.data); if (m.id && waits[m.id]) { waits[m.id](m.result); delete waits[m.id]; } };
const send = (method, params = {}) => new Promise(r => { const i = ++id; waits[i] = r; ws.send(JSON.stringify({ id: i, method, params })); });

await send('Page.enable'); await send('Network.enable');
if (auth) await send('Network.setExtraHTTPHeaders', { headers: { Authorization: 'Basic ' + auth } });
await send('Emulation.setDeviceMetricsOverride', { width: +w, height: +hgt, deviceScaleFactor: 1, mobile: +w < 700 });
await send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-color-scheme', value: scheme }] });
await send('Page.navigate', { url });
await sleep(3000);

let failed = 0;
for (const step of steps) {
  let r;                                       // a step that is cut off by the page navigating (a sign-in reloads it) is tried again on the new page
  for (let attempt = 0; attempt < 3; attempt++) {
    r = await send('Runtime.evaluate', { expression: `(async () => { ${step.js} })()`, awaitPromise: true, returnByValue: true });
    if (r && (r.result || r.exceptionDetails)) break;
    await sleep(1800);
  }
  const out = r.exceptionDetails ? 'EXCEPTION ' + (r.exceptionDetails.exception && r.exceptionDetails.exception.description) : JSON.stringify(r.result.value);
  let ok = true;
  if (step.expect !== undefined) { ok = r.result && JSON.stringify(r.result.value) === JSON.stringify(step.expect); if (!ok) failed++; }
  console.log((step.expect === undefined ? '  ' : ok ? 'PASS ' : 'FAIL ') + step.name + ' -> ' + out + (ok ? '' : '   (wanted ' + JSON.stringify(step.expect) + ')'));
  if (step.shot) {
    const dims = JSON.parse((await send('Runtime.evaluate', { expression: 'JSON.stringify({sh: document.documentElement.scrollHeight, sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth})', returnByValue: true })).result.value);
    if (dims.sw > dims.cw) { console.log('  OVERFLOW at ' + step.name, dims); failed++; }
    await send('Emulation.setDeviceMetricsOverride', { width: +w, height: Math.min(dims.sh, 3000), deviceScaleFactor: 1, mobile: +w < 700 });
    await sleep(200);
    const shot = await send('Page.captureScreenshot', { format: 'png' });
    writeFileSync(step.shot, Buffer.from(shot.data, 'base64'));
    await send('Emulation.setDeviceMetricsOverride', { width: +w, height: +hgt, deviceScaleFactor: 1, mobile: +w < 700 });
  }
}
console.log(failed ? `${failed} FAILED` : 'ALL PASSED');
ws.close(); chrome.kill();
process.exit(failed ? 1 : 0);
