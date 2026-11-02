// ui_check/shot.mjs: screenshot a page in headless Chrome at a real device width, in light or dark, and report sideways overflow.
//   node --experimental-websocket scripts/ui_check/shot.mjs <url> <out.png> <width> [height] [dark|light] [basicAuthBase64]
// Environment: FULL=0 for a viewport-sized shot (default is the whole page), WAIT=ms to wait after load (default 2500),
//   EVAL='js' to run a snippet in the page before the shot (for example to open a section), CHROME=/path/to/chrome.
// Prints  <out> {sw, cw, sh} ok|OVERFLOW  : sw wider than cw means the page scrolls sideways, which is a bug.
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

const [url, out, w = '390', hgt = '844', scheme = 'dark', auth = ''] = process.argv.slice(2);
const port = 9300 + Math.floor(Math.random() * 500);
const chrome = spawn(chromePath(),
  ['--headless=new', '--disable-gpu', `--remote-debugging-port=${port}`, `--user-data-dir=${mkdtempSync(join(tmpdir(), 'cdp'))}`, 'about:blank'],
  { stdio: 'ignore' });
const sleep = ms => new Promise(r => setTimeout(r, ms));
let target;
for (let i = 0; i < 50 && !target; i++) {
  await sleep(200);
  try { target = (await (await fetch(`http://127.0.0.1:${port}/json`)).json()).find(t => t.type === 'page'); } catch {}
}
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise(r => ws.onopen = r);
let id = 0; const waits = {};
ws.onmessage = e => { const m = JSON.parse(e.data); if (m.id && waits[m.id]) { waits[m.id](m.result); delete waits[m.id]; } };
const send = (method, params = {}) => new Promise(r => { const i = ++id; waits[i] = r; ws.send(JSON.stringify({ id: i, method, params })); });

await send('Page.enable');
await send('Network.enable');
if (auth) await send('Network.setExtraHTTPHeaders', { headers: { Authorization: 'Basic ' + auth } });
await send('Emulation.setDeviceMetricsOverride', { width: +w, height: +hgt, deviceScaleFactor: 1, mobile: +w < 700 });
await send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-color-scheme', value: scheme }] });
await send('Page.navigate', { url });
await sleep(+process.env.WAIT || 2500);
if (process.env.EVAL) { const r = await send('Runtime.evaluate', { expression: process.env.EVAL, awaitPromise: true }); if (r.exceptionDetails) console.log('EVAL ERROR', JSON.stringify(r.exceptionDetails.exception && r.exceptionDetails.exception.description)); await sleep(700); }
const ov = await send('Runtime.evaluate', { expression: 'JSON.stringify({sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth, sh: document.documentElement.scrollHeight})', returnByValue: true });
const dims = JSON.parse(ov.result.value);
console.log(out, dims, dims.sw > dims.cw ? 'OVERFLOW' : 'ok');
const full = process.env.FULL !== '0';
if (full) await send('Emulation.setDeviceMetricsOverride', { width: +w, height: Math.min(dims.sh, 4000), deviceScaleFactor: 1, mobile: +w < 700 });
await sleep(300);
const shot = await send('Page.captureScreenshot', { format: 'png' });
writeFileSync(out, Buffer.from(shot.data, 'base64'));
ws.close(); chrome.kill();
process.exit(0);
