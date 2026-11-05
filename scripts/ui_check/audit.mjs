// ui_check/audit.mjs: audit a real page, as rendered, for the things that are easy to get wrong and hard to see.
//   node --experimental-websocket scripts/ui_check/audit.mjs <url> [width] [dark|light] [basicAuthBase64]
// Environment: VIEWS='["#overview","#problems"]' visits each address fragment in turn (default: the page as loaded);
//   SETUP='js' runs a snippet in the page first (for example to open a call); CHROME=/path/to/chrome.
//
// What it checks, per view (error = must fix, warn = should look at):
//   error  sideways scroll (the page is wider than the window), so at 320 px wide it fails WCAG reflow
//   error  an interactive element with no accessible name; a duplicate id; an interactive target under 24 px (WCAG 2.5.8)
//   error  visible text below 4.5:1 (3:1 for large text) against what is behind it, measured from the real computed colours
//   warn   an interactive target under 44 px on a touch screen; no <main>, more than one <h1>, a missing <title> or lang
// Disabled controls and visually hidden text are skipped (WCAG exempts disabled controls). Text is measured against the colours
// stacked behind it, from the real computed styles.
// Prints one line per finding and a summary. Exit code 1 if any error.
import { existsSync } from 'node:fs';
import { spawn } from 'node:child_process';
import { mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

function chromePath() {
  const candidates = [process.env.CHROME, 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe', '/usr/bin/google-chrome', '/usr/bin/chromium',
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'];
  const found = candidates.find(c => c && existsSync(c));
  if (!found) throw new Error('Chrome not found. Set CHROME to its path.');
  return found;
}

const [url, w = '390', scheme = 'light', auth = ''] = process.argv.slice(2);
const views = process.env.VIEWS ? JSON.parse(process.env.VIEWS) : [''];
const touch = +w < 700;

const ANALYSE = `(() => {
  const out = [];
  const describe = el => {
    const id = el.id ? '#' + el.id : '', cls = typeof el.className === 'string' && el.className.trim() ? '.' + el.className.trim().split(/\\s+/).slice(0, 2).join('.') : '';
    const text = (el.innerText || el.getAttribute('aria-label') || '').trim().replace(/\\s+/g, ' ').slice(0, 28);
    return el.tagName.toLowerCase() + id + cls + (text ? ' "' + text + '"' : '');
  };
  const add = (sev, rule, el, msg) => out.push({ sev, rule, at: el ? describe(el) : '', msg });
  const shown = el => { const r = el.getBoundingClientRect(), cs = getComputedStyle(el); return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none'; };

  // --- the document
  if (!document.title.trim()) add('warn', 'title', null, 'the page has no <title>');
  if (!document.documentElement.lang) add('warn', 'lang', null, 'the <html> has no lang');
  const mains = document.querySelectorAll('main').length; if (mains !== 1) add('warn', 'landmark', null, mains + ' <main> elements (want 1)');
  const h1s = [...document.querySelectorAll('h1')].filter(shown).length; if (h1s > 1) add('warn', 'headings', null, h1s + ' visible <h1> elements');
  const seen = new Map(); document.querySelectorAll('[id]').forEach(e => seen.set(e.id, (seen.get(e.id) || 0) + 1));
  seen.forEach((n, id) => { if (n > 1) add('error', 'duplicate-id', document.getElementById(id), 'id "' + id + '" used ' + n + ' times'); });

  // --- sideways scroll, and what pokes out
  const vw = document.documentElement.clientWidth;
  if (document.documentElement.scrollWidth > vw) {
    add('error', 'overflow', null, 'the page scrolls sideways: ' + document.documentElement.scrollWidth + ' px wide in a ' + vw + ' px window');
    let n = 0;
    for (const el of document.querySelectorAll('body *')) { if (n >= 4) break; if (shown(el) && el.getBoundingClientRect().right > vw + 1 && !el.closest('[style*="position:absolute"]')) { add('error', 'overflow-cause', el, 'reaches ' + Math.round(el.getBoundingClientRect().right) + ' px'); n++; } }
  }

  // --- interactive elements: a name, and a size
  const name = el => {
    const a = el.getAttribute('aria-label'); if (a && a.trim()) return a.trim();
    const lb = el.getAttribute('aria-labelledby'); if (lb) { const t = lb.split(' ').map(i => (document.getElementById(i) || {}).textContent || '').join(' ').trim(); if (t) return t; }
    if (el.labels && el.labels.length) { const t = [...el.labels].map(l => l.textContent).join(' ').trim(); if (t) return t; }
    if (el.tagName === 'INPUT' && ['button', 'submit'].includes(el.type) && el.value) return el.value;
    const t = (el.innerText || el.textContent || '').trim(); if (t) return t;
    return (el.getAttribute('title') || '').trim();
  };
  const SEL = 'a[href], button, input:not([type=hidden]), select, textarea, summary, [role=button], [tabindex]:not([tabindex="-1"])';
  document.querySelectorAll(SEL).forEach(el => {
    if (el.closest('[hidden]') || el.disabled || el.getAttribute('aria-disabled') === 'true') return;
    let r = el.getBoundingClientRect();
    if (r.width < 4 || r.height < 4) { const l = el.labels && el.labels[0]; if (l) r = l.getBoundingClientRect(); }      // a visually hidden input: its label is the target
    if (!(r.width > 0 && r.height > 0)) return;
    if (!name(el)) add('error', 'no-name', el, 'an interactive element with no accessible name');
    const inText = el.tagName === 'A' && getComputedStyle(el).display === 'inline';                                       // a link inside a sentence is exempt from the size rule
    if (!inText) {
      const small = Math.min(r.width, r.height);
      if (small < 24) add('error', 'target-24', el, Math.round(r.width) + 'x' + Math.round(r.height) + ' px (WCAG minimum 24)');
      else if (${touch} && small < 44) add('warn', 'target-44', el, Math.round(r.width) + 'x' + Math.round(r.height) + ' px (44 recommended on touch)');
    }
  });

  // --- the contrast of the text that is actually on screen
  const parse = c => { const m = c.match(/rgba?\\(([^)]+)\\)/); if (!m) return null; const p = m[1].split(/[ ,\\/]+/).filter(Boolean).map(Number); return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 }; };
  const over = (top, under) => ({ r: top.r * top.a + under.r * (1 - top.a), g: top.g * top.a + under.g * (1 - top.a), b: top.b * top.a + under.b * (1 - top.a), a: 1 });
  const lum = c => { const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b); };
  const ratio = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
  const page = parse(getComputedStyle(document.body).backgroundColor) || { r: 255, g: 255, b: 255, a: 1 };
  const behind = el => { const chain = []; for (let e = el; e; e = e.parentElement) chain.push(e); let bg = { ...page, a: 1 }; for (const e of chain.reverse()) { const c = parse(getComputedStyle(e).backgroundColor); if (c && c.a > 0) bg = over(c, bg); } return bg; };
  const done = new Set();
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let n = walker.nextNode(); n; n = walker.nextNode()) {
    const el = n.parentElement;
    if (!el || !n.textContent.trim() || !shown(el) || el.closest('.sr, [hidden], script, style, :disabled, [aria-disabled=true]')) continue;
    const cs = getComputedStyle(el); let fg = parse(cs.color); if (!fg) continue;
    let op = 1; for (let e = el; e; e = e.parentElement) op *= parseFloat(getComputedStyle(e).opacity);
    const bg = behind(el); fg = over({ ...fg, a: fg.a * op }, bg);
    const size = parseFloat(cs.fontSize), bold = parseInt(cs.fontWeight, 10) >= 700, large = size >= 24 || (size >= 18.66 && bold);
    const need = large ? 3 : 4.5, got = ratio(fg, bg);
    if (got < need) { const key = describe(el) + got.toFixed(2); if (!done.has(key)) { done.add(key); add('error', 'contrast', el, got.toFixed(2) + ':1, needs ' + need + ' (' + Math.round(size) + ' px)'); } }
  }
  return { out, touch: matchMedia('(pointer: coarse)').matches };
})()`;

const port = 9900 + Math.floor(Math.random() * 90);
const chrome = spawn(chromePath(), ['--headless=new', '--disable-gpu', `--remote-debugging-port=${port}`,
  `--user-data-dir=${mkdtempSync(join(tmpdir(), 'cdp'))}`, 'about:blank'], { stdio: 'ignore' });
const sleep = ms => new Promise(r => setTimeout(r, ms));
let target;
for (let i = 0; i < 50 && !target; i++) { await sleep(200); try { target = (await (await fetch(`http://127.0.0.1:${port}/json`)).json()).find(t => t.type === 'page'); } catch {} }
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise(r => ws.onopen = r);
let id = 0; const waits = {};
ws.onmessage = e => { const m = JSON.parse(e.data); if (m.id && waits[m.id]) { waits[m.id](m.result); delete waits[m.id]; } };
const send = (method, params = {}) => new Promise(r => { const i = ++id; waits[i] = r; ws.send(JSON.stringify({ id: i, method, params })); });
const run = async js => (await send('Runtime.evaluate', { expression: js, awaitPromise: true, returnByValue: true })).result;

await send('Page.enable'); await send('Network.enable');
if (auth) await send('Network.setExtraHTTPHeaders', { headers: { Authorization: 'Basic ' + auth } });
await send('Emulation.setDeviceMetricsOverride', { width: +w, height: 900, deviceScaleFactor: 1, mobile: touch });
if (touch) await send('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 1 });
await send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-color-scheme', value: scheme }] });
// The admin page defaults to dark whatever the system says, so state the theme the way a person would, by choosing it.
await send('Page.addScriptToEvaluateOnNewDocument', { source: `try{localStorage.setItem('dd:theme',${JSON.stringify(scheme)})}catch(e){}` });
await send('Page.navigate', { url });
await sleep(3000);
if (process.env.SETUP) { await run(`(async () => { ${process.env.SETUP} })()`); await sleep(1500); }

let errors = 0, warns = 0;
for (const view of views) {
  if (view) { await run(`location.hash = ${JSON.stringify(view)}`); await sleep(900); }
  const r = (await run(ANALYSE)).value;
  const label = (view || 'page') + ' @' + w + 'px ' + scheme + (r.touch ? ' touch' : '');
  const found = r.out;
  found.forEach(f => console.log(`${f.sev === 'error' ? 'ERROR' : 'warn '} ${label} [${f.rule}] ${f.at} ${f.msg}`));
  const e = found.filter(f => f.sev === 'error').length; errors += e; warns += found.length - e;
  if (!found.length) console.log(`ok    ${label}`);
}
console.log(errors ? `${errors} ERRORS, ${warns} warnings` : `no errors, ${warns} warnings`);
ws.close(); chrome.kill();
process.exit(errors ? 1 : 0);
