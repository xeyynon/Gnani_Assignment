// ui_check/snapshots.mjs: take a full-page screenshot of every page, in every state, theme and device size, into snapshots/latest/.
//   SNAP_PIN=<shop pin> SNAP_ADMIN_PASSWORD=<admin password> node --experimental-websocket scripts/ui_check/snapshots.mjs <base-url> [out-dir] [only]
// Meant to be pointed at the made-up-data preview (python -m dukaan_dost.preview --port 8861 --no-browser), which prints both secrets.
// `only` is a page name (call-page, dashboard, admin) to retake just that one. CHROME=/path/to/chrome overrides the browser.
//
// Layout and naming (so a file name says what it is):
//   snapshots/latest/<page>/<NN>-<state>/<theme>-<device>-<width>.png      e.g. snapshots/latest/admin/02-problems/dark-phone-390.png
//   snapshots/latest/INDEX.md                                               what is in the folder, when, and from which commit
//   snapshots/latest/manifest.json                                          every image taken and whether it scrolled sideways
// Retaking a snapshot overwrites the file with the same name, so `git diff --stat snapshots/latest/` shows which screens changed.
// The older releases are in snapshots/history/ (scripts/ui_check/snapshot_release.py takes them from git); for those this tool is run with
// SNAP_PAGES='[{"name":"call-page","path":"/","auth":"","states":[["landing",""]]}]' (auth is a full Authorization header value),
// SNAP_DEVICES='[["phone",390,844],["desktop",1280,900]]' and SNAP_NO_INDEX=1.
import { existsSync, mkdirSync, writeFileSync, mkdtempSync, rmSync } from 'node:fs';
import { spawn, execSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import { join, relative } from 'node:path';

const [base, outDir = 'snapshots/latest', only = ''] = process.argv.slice(2);
if (!base) { console.error('usage: snapshots.mjs <base-url> [out-dir] [only]'); process.exit(2); }
const basic = (user, pw) => 'Basic ' + Buffer.from(`${user}:${pw}`).toString('base64');
const DASH = process.env.SNAP_PIN ? basic('shop', process.env.SNAP_PIN) : '';
const ADMIN = basic('admin', process.env.SNAP_ADMIN_PASSWORD || '');

const THEMES = ['light', 'dark'];
const DEVICES = process.env.SNAP_DEVICES ? JSON.parse(process.env.SNAP_DEVICES) : [['phone', 390, 844], ['tablet', 768, 1024], ['desktop', 1280, 900]];
const SHOP = 'demo_kirana';

const ORDER = { items: [{ name: 'Toor dal', qty: 2, unit: 'kg', line_total: 280 }, { name: 'Sunflower oil', qty: 1, unit: 'litre', line_total: 142 },
  { name: 'Parle-G biscuits', qty: 4, unit: 'packet', line_total: 40 }], total: 462 };
const LOAN = { type: 'loan', heard_amount: 150000, kind: 'working capital', business: 'kirana shop', place: 'Hyderabad', margin_money: 150000,
  project_cost: 200000, covered: true, scheme: 'Mudra Shishu', annual_rate_pct: 11, loan_amount: 150000, own_contribution: 50000,
  monthly_instalment: 4900, repayment_months: 36, moratorium_months: 6, total_repayment: 176400, total_interest: 26400, indicative: true };
const view = hash => `location.hash=${JSON.stringify(hash)}`;
// A shop with nothing in it yet: what the empty lists say (made up, like everything else here).
// A made-up call in progress, in the shape the dashboard's data feed gives for a live call (conversation, order so far, loan quote).
const LIVE_CALL = { seconds: 74, channel: 'phone', language: 'hi-IN',
  lines: [{ who: 'agent', text: 'Namaste, Dukaan Dost mein aapka swagat hai. Aap kya lena chahenge?' }, { who: 'caller', text: 'Do kilo chawal aur ek litre tel chahiye.' },
    { who: 'agent', text: 'Theek hai. Do kilo chawal aur ek litre sunflower oil. Kuch aur?' }, { who: 'caller', text: 'Haan, char Maggi bhi dena.' },
    { who: 'agent', text: 'Char Maggi noodles add kar diye. Payment kaise karenge?' }, { who: 'caller', text: 'UPI se kar dunga.' },
    { who: 'agent', text: 'Theek hai, UPI. Business loan ke baare mein bhi pooch sakte hain.' }, { who: 'caller', text: 'Haan, ek lakh margin money hai. Loan kitna milega?' }],
  order: { total: 341, items: [{ name: 'Rice', qty: 2, unit: 'kg', line_total: 120 }, { name: 'Sunflower oil', qty: 1, unit: 'litre', line_total: 165 }, { name: 'Maggi noodles', qty: 4, unit: 'pack', line_total: 56 }] },
  loan: { heard_amount: 100000, kind: 'margin_money', business: 'kirana', place: 'Nandyal', margin_money: 100000, project_cost: 500000, covered: true, scheme: 'Mudra Kishor',
    annual_rate_pct: 10, loan_amount: 400000, own_contribution: 100000, monthly_instalment: 9000, repayment_months: 60, moratorium_months: 6, total_interest: 140000 } };
const EMPTY_SHOP = { title: 'New Shop', shop: 'new', summary: { orders_today: 0, sales_today: 0, orders_total: 0, orders_yesterday: 0, sales_yesterday: 0, orders_yesterday_same_time: 0, sales_yesterday_same_time: 0, udhaar_outstanding: 0, customers_owing: 0, loans_today: 0, loans_total: 0, calls_today: 0, calls_total: 0, needs_attention: 0 }, trend: [], orders: [], loans: [], calls: [], ledger: [], live: [], problems: [] };

// A page is a URL, the credentials it needs, and the states to put it in. A state is a snippet run in the page, then a short wait.
const PAGES = process.env.SNAP_PAGES ? JSON.parse(process.env.SNAP_PAGES) : [
  { name: 'call-page', path: '/', auth: '', states: [
    ['idle', ''],
    ['order-in-progress', `renderOrder(${JSON.stringify(ORDER)})`],
    ['order-and-loan-quote', `renderLoan(${JSON.stringify(LOAN)})`],
  ] },
  // The sign-in pages are what a browser with no session sees. showResult is the page's own function, so each answer is drawn by the real code.
  { name: 'sign-in-shop', path: `/s/${SHOP}/dashboard`, auth: '', states: [
    ['idle', ''],
    ['pin-typed', `$('secret').value='4821'`],
    ['pin-shown', 'peek()'],
    ['empty-submit', `peek(); $('secret').value=''; showResult(400, {empty: true})`],
    ['wrong-pin', `$('secret').value='4822'; showResult(401, {wrong: true, remaining: 3})`],
    ['locked', `showResult(429, {locked: true, retry_after: 42})`],
  ] },
  { name: 'sign-in-shop-without-a-pin', path: '/s/no_pin_stores/dashboard', auth: '', states: [['idle', '']] },
  { name: 'sign-in-admin', path: '/admin', auth: '', states: [
    ['idle', ''],
    ['wrong-password', `$('secret').value='nope'; showResult(401, {wrong: true, remaining: 2})`],
    ['locked', `showResult(429, {locked: true, retry_after: 42})`],
  ] },
  { name: 'dashboard', path: `/s/${SHOP}/dashboard`, auth: DASH, states: [
    ['overview', view('#overview')],
    ['orders', view('#orders')],
    ['credit-book', view('#credit')],
    ['loan-enquiries', view('#loans')],
    ['calls', view('#calls')],
    ['overview-scrolled-long-name', `${view('#overview')};$('title').textContent='Dukaan Dost (real records, a copy)';window.scrollTo(0,40)`],   // the sticky top bar over content, with a name long enough to make it two rows
    ['tour-step-1', `${view('#overview')};startTour($('tourbtn'))`],
    ['tour-step-3', `${view('#overview')};startTour($('tourbtn'));showTourStep(2)`],
    ['empty-orders', `window.fetch=()=>new Promise(()=>{});render(${JSON.stringify(EMPTY_SHOP)});${view('#orders')}`],
    ['empty-calls', `window.fetch=()=>new Promise(()=>{});render(${JSON.stringify(EMPTY_SHOP)});${view('#calls')}`],
    // The Live view: one made-up phone call in progress (a fixed picture, not the preview's call that comes and goes), and the view with no call.
    ['live-call', `window.fetch=()=>new Promise(()=>{});render(${JSON.stringify({ ...EMPTY_SHOP, live: [LIVE_CALL] })});${view('#live')}`],
    ['live-empty', `window.fetch=()=>new Promise(()=>{});render(${JSON.stringify(EMPTY_SHOP)});${view('#live')}`],
  ] },
  { name: 'admin', path: '/admin', auth: ADMIN, states: [
    ['overview', view('#overview')],
    ['problems', view('#problems')],
    ['activity', view('#activity')],
    ['add-a-shop', view('#add')],
    ['edit-a-working-shop', view(`#edit/${SHOP}`)],
    ['edit-a-broken-shop', view('#edit/broken_shop')],
  ] },
];

function chromePath() {
  const found = [process.env.CHROME, 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe', '/usr/bin/google-chrome', '/usr/bin/chromium',
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'].find(c => c && existsSync(c));
  if (!found) throw new Error('Chrome not found. Set CHROME to its path.');
  return found;
}
const sleep = ms => new Promise(r => setTimeout(r, ms));
const num = n => String(n).padStart(2, '0');

async function session(page, theme, [device, width, height], taken) {
  const port = 9100 + Math.floor(Math.random() * 700), profile = mkdtempSync(join(tmpdir(), 'cdp'));
  const chrome = spawn(chromePath(), ['--headless=new', '--disable-gpu', `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, 'about:blank'], { stdio: 'ignore' });
  try {
    let target;
    for (let i = 0; i < 50 && !target; i++) { await sleep(200); try { target = (await (await fetch(`http://127.0.0.1:${port}/json`)).json()).find(t => t.type === 'page'); } catch {} }
    const ws = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise(r => ws.onopen = r);
    let id = 0; const waits = {};
    ws.onmessage = e => { const m = JSON.parse(e.data); if (m.id && waits[m.id]) { waits[m.id](m.result); delete waits[m.id]; } };
    const send = (method, params = {}) => new Promise(r => { const i = ++id; waits[i] = r; ws.send(JSON.stringify({ id: i, method, params })); });
    const phone = width < 700;
    await send('Page.enable'); await send('Network.enable');
    if (page.auth) await send('Network.setExtraHTTPHeaders', { headers: { Authorization: page.auth } });
    await send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: phone });
    if (phone) await send('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 1 });
    await send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-color-scheme', value: theme }] });
    await send('Page.addScriptToEvaluateOnNewDocument', { source: `try{localStorage.setItem('dd:theme',${JSON.stringify(theme)});localStorage.setItem('dd:tour','1')}catch(e){}` });
    await send('Page.navigate', { url: base + page.path });
    await sleep(3200);
    for (const [i, [state, js]] of page.states.entries()) {
      if (js) { const r = await send('Runtime.evaluate', { expression: js, awaitPromise: true }); if (r.exceptionDetails) console.log('  STATE ERROR', page.name, state, JSON.stringify(r.exceptionDetails.exception && r.exceptionDetails.exception.description)); await sleep(1100); }
      const m = JSON.parse((await send('Runtime.evaluate', { expression: 'JSON.stringify({sw:document.documentElement.scrollWidth,cw:document.documentElement.clientWidth,sh:document.documentElement.scrollHeight,t:document.title})', returnByValue: true })).result.value);
      await send('Emulation.setDeviceMetricsOverride', { width, height: Math.min(Math.max(m.sh, height), 5000), deviceScaleFactor: 1, mobile: phone });
      await sleep(250);
      const shot = await send('Page.captureScreenshot', { format: 'png' });
      await send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: phone });
      const dir = join(outDir, page.name, `${num(i + 1)}-${state}`); mkdirSync(dir, { recursive: true });
      const file = join(dir, `${theme}-${device}-${width}.png`);
      writeFileSync(file, Buffer.from(shot.data, 'base64'));
      const bad = m.sw > m.cw;
      taken.push({ page: page.name, n: i + 1, state, theme, device, width, file: file.replace(/\\/g, '/'), overflow: bad });
      console.log(bad ? 'OVERFLOW' : 'ok      ', file);
    }
    ws.close();
  } finally { chrome.kill(); try { rmSync(profile, { recursive: true, force: true }); } catch {} }
}

const taken = [];
for (const page of PAGES.filter(p => !only || p.name === only))
  for (const theme of THEMES) for (const device of DEVICES) await session(page, theme, device, taken);

// The index: one section per page, one table per state, so the folder explains itself.
let commit = 'unknown'; try { commit = execSync('git rev-parse --short HEAD', { encoding: 'utf8' }).trim(); } catch {}
const lines = ['# Snapshots', '',
  'Full-page screenshots of every page in every state, in light and dark, at phone, tablet and desktop widths. All data is made up (the preview\'s demo shop).', '',
  `Taken ${new Date().toISOString().slice(0, 10)} from commit \`${commit}\` by \`scripts/ui_check/snapshots.mjs\`. Retake with the command in that file\'s header; same-named files are overwritten.`, '',
  'Naming: `<page>/<NN>-<state>/<theme>-<device>-<width>.png`. Phone is 390 px, tablet 768 px, desktop 1280 px.', ''];
for (const page of PAGES) {
  const mine = taken.filter(t => t.page === page.name); if (!mine.length) continue;
  lines.push(`## ${page.name}`, '');
  for (const [i, [state]] of page.states.entries()) {
    lines.push(`### ${num(i + 1)} ${state.replace(/-/g, ' ')}`, '', '| Device | Light | Dark |', '|---|---|---|');
    for (const [device, width] of DEVICES) {
      const rel = t => relative(outDir, t.file).replace(/\\/g, '/');
      const f = th => { const t = mine.find(x => x.n === i + 1 && x.theme === th && x.device === device); return t ? `[${rel(t)}](${rel(t)})${t.overflow ? ' (scrolls sideways)' : ''}` : ''; };
      lines.push(`| ${device} ${width} | ${f('light')} | ${f('dark')} |`);
    }
    lines.push('');
  }
}
if (!only && !process.env.SNAP_NO_INDEX) writeFileSync(join(outDir, 'INDEX.md'), lines.join('\n'));
if (!only) writeFileSync(join(outDir, 'manifest.json'), JSON.stringify(taken.map(t => ({ ...t, file: relative(outDir, t.file).replace(/\\/g, '/') })), null, 1));
const sideways = taken.filter(t => t.overflow);
console.log(`\n${taken.length} snapshots in ${outDir}/` + (sideways.length ? `, ${sideways.length} scroll sideways` : ', none scroll sideways'));
process.exit(sideways.length ? 1 : 0);
