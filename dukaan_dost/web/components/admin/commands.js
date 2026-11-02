/* ---- commands: the page asks the server to change things over a WebSocket (admin.py explains why, and the token) ---- */
let sock = null, opening = null, nextId = 1;
const waiting = new Map();
const CALL_TIMEOUT_MS = 20000;

function openSocket() {
  return fetch('/admin/token', { cache: 'no-store', credentials: 'same-origin' }).then(r => {
    if (!r.ok) throw new Error('You are signed out. Reload the page and sign in again.');
    return r.json();
  }).then(({ token }) => new Promise((resolve, reject) => {
    const ws = new WebSocket((location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/admin/ws');
    ws.onopen = () => ws.send(JSON.stringify({ cmd: 'hello', token }));
    ws.onmessage = ev => {
      const m = JSON.parse(ev.data);
      if (m.type === 'ready') { sock = ws; resolve(ws); return; }
      const w = waiting.get(m.id);
      if (w) { waiting.delete(m.id); if (m.ok) w.resolve(m); else w.reject(new Error(m.error)); }
    };
    ws.onclose = () => {
      if (sock === ws) sock = null;
      waiting.forEach(w => w.reject(new Error('The connection to the agent closed. Try again.')));
      waiting.clear();
      reject(new Error('Could not connect to the agent.'));
    };
    ws.onerror = () => {};
  }));
}

async function adminCall(cmd, fields) {
  if (!sock || sock.readyState !== WebSocket.OPEN) {
    opening = opening || openSocket().finally(() => { opening = null; });
    await opening;
  }
  const id = nextId++;
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => { waiting.delete(id); reject(new Error('The agent did not answer. Check that it is running, then try again.')); }, CALL_TIMEOUT_MS);
    waiting.set(id, { resolve: m => { clearTimeout(timer); resolve(m); }, reject: e => { clearTimeout(timer); reject(e); } });
    sock.send(JSON.stringify(Object.assign({ id, cmd }, fields)));
  });
}

async function refreshNow() {               // draw the latest data straight away, after a change (the regular poll carries on by itself)
  const r = await fetch('/admin/data', { cache: 'no-store', credentials: 'same-origin' });
  if (r.ok) { render(await r.json()); lastOk = Date.now(); }
}

function say(el, text, kind) { el.textContent = text; el.className = 'msg' + (kind ? ' ' + kind : ''); }   // a message under a form
async function run(button, msgEl, working, job) {      // disable the button while a command runs; show the outcome in words
  button.disabled = true; say(msgEl, working);
  try { await job(); } catch (e) { say(msgEl, e.message, 'bad'); } finally { button.disabled = false; }
}
