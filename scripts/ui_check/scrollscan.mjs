// ui_check/scrollscan.mjs: find text that collides with other text, or crosses the edge of a box it is not in, with the page scrolled.
//   node --experimental-websocket scripts/ui_check/scrollscan.mjs <url> <width> <light|dark> [basicAuthBase64] [longTitle]
// The audit and the pictures are taken at the top of the page, which is where a sticky bar has nothing under it; this scrolls to the top,
// 40 px, 300 px, the middle and the bottom, and at each stop looks at every piece of visible text:
//   collision : two pieces of visible text, from elements that do not contain each other, whose boxes overlap
//   crossing  : a piece of text whose box is partly inside and partly outside a box that has a border or a fill, and is not inside it
//               (a solid sticky or fixed bar is left out: content scrolling under it is what it is for; a see-through one is not)
// "Visible" means the element really is what the browser draws at the middle of that text (so text hidden under a solid bar does not count).
// Environment: SCAN_TITLE='a long shop name' sets the page's #title first (a longer name makes the top bar two rows); SETUP='js' runs first;
// DD_TOUR_SEEN=0 leaves the first-visit tour on. Prints one line per finding and "scan ok" when there are none. Exit 1 on findings.
import { spawn } from 'node:child_process';
import { existsSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const [url, width = '390', scheme = 'light', auth = ''] = process.argv.slice(2);
function chromePath() {
  const found = [process.env.CHROME, 'C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
    '/usr/bin/google-chrome', '/usr/bin/chromium', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'].find(c => c && existsSync(c));
  if (!found) throw new Error('Chrome not found. Set CHROME to its path.');
  return found;
}
const sleep = ms => new Promise(r => setTimeout(r, ms));
const port = 9900 + Math.floor(Math.random() * 90);
const chrome = spawn(chromePath(), ['--headless=new', '--disable-gpu', `--remote-debugging-port=${port}`, `--user-data-dir=${mkdtempSync(join(tmpdir(), 'cdp'))}`, 'about:blank'], { stdio: 'ignore' });
let target;
for (let i = 0; i < 150 && !target; i++) { await sleep(200); try { target = (await (await fetch(`http://127.0.0.1:${port}/json`)).json()).find(t => t.type === 'page'); } catch {} }
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise(r => ws.onopen = r);
let id = 0; const waits = {};
ws.onmessage = e => { const m = JSON.parse(e.data); if (m.id && waits[m.id]) { waits[m.id](m.result); delete waits[m.id]; } };
const send = (method, params = {}) => new Promise(r => { const i = ++id; waits[i] = r; ws.send(JSON.stringify({ id: i, method, params })); });
const run = async js => (await send('Runtime.evaluate', { expression: js, awaitPromise: true, returnByValue: true })).result.value;

const scan = `(() => {
  const found = [], vw = innerWidth, vh = innerHeight;
  const tidy = e => (e.id ? '#' + e.id : '') + (typeof e.className === 'string' && e.className ? '.' + e.className.trim().split(/\\s+/).join('.') : '') || e.tagName.toLowerCase();
  const closedDetails = e => { const d = e.closest('details:not([open])'); return !!d && !e.closest('summary'); };      // what a closed <details> hides still has a box
  const isSolid = cs => cs.backgroundColor.startsWith('rgb(') || cs.backgroundColor.endsWith(', 1)');       // no regex here: this text sits inside a template string
  const stuck = e => { const p = getComputedStyle(e).position; return p === 'sticky' || p === 'fixed'; };
  const solidBarOf = e => { for (let x = e; x && x !== document.body; x = x.parentElement) if (stuck(x) && isSolid(getComputedStyle(x))) return x; return null; };
  // a sticky or fixed element that holds text but has no solid background lets the page show through it as it scrolls
  for (const e of document.querySelectorAll('body *')) {
    if (!stuck(e)) continue;
    const cs = getComputedStyle(e), r = e.getBoundingClientRect();
    if (r.width < 20 || r.height < 12 || cs.visibility === 'hidden' || e.hidden || cs.display === 'none' || !e.innerText || !e.innerText.trim()) continue;
    if (!isSolid(cs) && !solidBarOf(e) && cs.pointerEvents !== 'none') found.push('see-through: ' + tidy(e) + ' is ' + cs.position + ' with text and no solid background');
  }
  const boxes = [];                                              // visible pieces of text: {el, r, s}
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let n; (n = walker.nextNode());) {
    const t = n.textContent.trim(); const el = n.parentElement;
    if (!t || !el || el.closest('script,style,svg,[hidden],.sr') || closedDetails(el)) continue;
    const cs = getComputedStyle(el); if (cs.visibility === 'hidden' || cs.display === 'none' || Number(cs.opacity) === 0) continue;
    const range = document.createRange(); range.selectNodeContents(n);
    for (const r of range.getClientRects()) {
      if (r.width < 2 || r.height < 2 || r.bottom < 0 || r.top > vh || r.right < 0 || r.left > vw) continue;
      const cx = Math.min(vw - 1, Math.max(0, r.left + r.width / 2)), cy = Math.min(vh - 1, Math.max(0, r.top + r.height / 2));
      const top = document.elementFromPoint(cx, cy);
      if (!top || !(top === el || el.contains(top) || top.contains(el))) continue;          // covered by something else: not visible text
      boxes.push({ el, r, s: t.slice(0, 28), onTop: !!solidBarOf(el) });
    }
  }
  const inter = (a, b) => Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left)) * Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top));
  for (let i = 0; i < boxes.length; i++) for (let j = i + 1; j < boxes.length; j++) {
    const a = boxes[i], b = boxes[j];
    if (a.onTop || b.onTop) continue;
    if (a.el === b.el || a.el.contains(b.el) || b.el.contains(a.el)) continue;
    const area = inter(a.r, b.r), small = Math.min(a.r.width * a.r.height, b.r.width * b.r.height);
    if (area > 6 && area > small * 0.12) found.push('collision: "' + a.s + '" (' + tidy(a.el) + ') over "' + b.s + '" (' + tidy(b.el) + ')');
  }
  // text crossing the edge of a box (a border or a fill) it is not inside
  const frames = [...document.querySelectorAll('body *')].filter(e => {
    const cs = getComputedStyle(e), r = e.getBoundingClientRect();
    if (r.width < 8 || r.height < 8 || cs.display === 'contents' || cs.visibility === 'hidden' || closedDetails(e)) return false;
    const border = ['Top', 'Right', 'Bottom', 'Left'].some(s => parseFloat(cs['border' + s + 'Width']) > 0 && cs['border' + s + 'Style'] !== 'none');
    const fill = cs.backgroundColor !== 'rgba(0, 0, 0, 0)' && cs.backgroundColor !== 'transparent';
    if (stuck(e) && isSolid(cs)) return false;     // a solid bar over scrolling content is meant to cover it
    return (border || fill) && !['HTML', 'BODY'].includes(e.tagName);
  });
  for (const b of boxes) for (const f of frames) {
    if (b.onTop) continue;
    if (f === b.el || f.contains(b.el) || b.el.contains(f)) continue;
    const fr = f.getBoundingClientRect(), area = inter(b.r, fr), mine = b.r.width * b.r.height;
    if (area > 6 && area < mine * 0.92 && area > mine * 0.12) found.push('crossing: "' + b.s + '" (' + tidy(b.el) + ') is half inside the box ' + tidy(f));
  }
  return [...new Set(found)].slice(0, 12);
})()`;

await send('Page.enable'); await send('Network.enable');
if (auth) await send('Network.setExtraHTTPHeaders', { headers: { Authorization: 'Basic ' + auth } });
await send('Emulation.setDeviceMetricsOverride', { width: Number(width), height: 800, deviceScaleFactor: 1, mobile: Number(width) < 500 });
await send('Page.addScriptToEvaluateOnNewDocument', { source: `try{localStorage.setItem('dd:theme',${JSON.stringify(scheme)});${process.env.DD_TOUR_SEEN === '0' ? '' : "localStorage.setItem('dd:tour','1');"}}catch(e){}` });
await send('Page.navigate', { url });
await sleep(3500);
if (process.env.SCAN_TITLE) await run(`(() => { const t = document.getElementById('title'); if (t) t.textContent = ${JSON.stringify(process.env.SCAN_TITLE)}; })()`);
if (process.env.SETUP) { await run(`(async () => { ${process.env.SETUP} })()`); await sleep(1200); }
const total = await run('document.documentElement.scrollHeight');
const stops = [...new Set([0, 40, 300, Math.round(total / 2), Math.max(0, total - 800)])];
let bad = 0;
for (const y of stops) {
  await run(`window.scrollTo(0, ${y})`); await sleep(350);
  for (const f of await run(scan)) { bad++; console.log(`finding @${width}px ${scheme} scroll ${y}: ${f}`); }
}
console.log(bad ? `scan: ${bad} finding(s)` : `scan ok @${width}px ${scheme} (${stops.length} scroll positions)`);
chrome.kill();
process.exit(bad ? 1 : 0);
