/* ---- the sign-in page: one GET with the PIN in a header, then the server sets a cookie (login.py explains why) ---- */
const root = $('login'), kind = root.dataset.kind, noPin = root.dataset.nopin === '1';
let busy = false, lockTimer = null;

function setMessage(text, tone) {
  const m = $('msg');
  m.textContent = text || '';
  m.className = 'login-alert' + (tone ? ' ' + tone : '');
  m.hidden = !text;
}
function setBusy(on) {
  busy = on;
  $('go').setAttribute('aria-busy', on ? 'true' : 'false');
  $('go').textContent = on ? 'Signing in...' : 'Sign in';
}
function setDisabled(off) { $('secret').disabled = off; $('go').disabled = off; $('peek').disabled = off; $('keep').disabled = off; }
function startLock(wait) {                                     // the form stays shut and counts down, so nobody keeps guessing blind
  clearInterval(lockTimer);
  const end = Date.now() + wait * 1000;
  setDisabled(true);
  const tick = () => {
    const left = Math.ceil((end - Date.now()) / 1000);
    if (left <= 0) { clearInterval(lockTimer); setMessage('', ''); setDisabled(false); $('secret').focus(); return; }
    setMessage(lockText(left), '');
  };
  tick();
  lockTimer = setInterval(tick, 1000);
}
function showResult(status, data) {                            // also what the snapshots call, to show each state without a real wrong guess
  const o = loginOutcome(status, data, kind);
  if (o.kind === 'ok') {
    setMessage(o.text, 'good');
    location.reload();                                         // the same address now answers with the page
    setTimeout(() => { setBusy(false); setMessage('Signed in, but this browser did not keep the sign-in. Allow cookies for this site and try again.', ''); }, 4000);
    return;
  }
  setBusy(false);
  if (o.kind === 'locked') { startLock(o.wait); return; }
  setMessage(o.text, '');
  $('secret').setAttribute('aria-invalid', 'true');
  $('secret').focus();
  $('secret').select();
}
async function submit(e) {
  e.preventDefault();
  if (busy || $('secret').disabled) return;
  const secret = $('secret').value;
  $('secret').removeAttribute('aria-invalid');
  if (!secret) { showResult(400, { empty: true }); return; }
  setBusy(true); setMessage('', '');
  try {
    const r = await fetch(root.dataset.session + ($('keep').checked ? '/keep' : ''), {
      cache: 'no-store', credentials: 'same-origin', headers: { Authorization: credentialHeader(kind === 'admin' ? 'admin' : 'shop', secret) } });
    let data = {};
    try { data = await r.json(); } catch (err) { /* a reply with no JSON is handled by its status */ }
    showResult(r.status, data);
  } catch (err) { showResult(0, {}); }
}

function peek() {
  const input = $('secret'), show = input.type === 'password';
  input.type = show ? 'text' : 'password';
  $('peek').setAttribute('aria-pressed', show ? 'true' : 'false');
  $('peek').setAttribute('aria-label', (show ? 'Hide ' : 'Show ') + whatWord(kind));
  $('peek').querySelector('use').setAttribute('href', show ? '#i-eye-off' : '#i-eye');
  input.focus();
}
function switchKeys() {                                        // a PIN is usually digits, but a chosen one may use letters
  const input = $('secret'), numeric = input.getAttribute('inputmode') === 'numeric';
  input.setAttribute('inputmode', numeric ? 'text' : 'numeric');
  $('kbd').textContent = numeric ? 'Use number pad' : 'Use letters';
  input.focus();
}

(function setup() {
  const w = loginWords(kind, noPin);
  const b = h('b', { text: document.querySelector('#user').value });
  $('login-sub').replaceChildren(document.createTextNode(w.sub + (kind === 'admin' ? '' : ' for ')), kind === 'admin' ? '' : b);
  $('secret-label').textContent = w.label;
  $('secret').placeholder = w.placeholder;
  $('peek').setAttribute('aria-label', 'Show ' + whatWord(kind));
  $('help').textContent = w.help;
  const links = [];
  if (w.back && root.dataset.back) links.push(h('a', { href: root.dataset.back, text: 'Back to the call page' }));
  if (w.admin) links.push(h('a', { href: '/admin', text: 'Admin sign in' }));
  $('links').replaceChildren(...links);
  if (kind === 'shop') $('kbd').hidden = false;
  else $('secret').setAttribute('inputmode', 'text');
  if (kind === 'admin') $('user').value = 'admin';
  if (noPin) {
    setMessage('No PIN has been set for this shop yet. Ask the administrator to set one, then come back.', 'info');
    setDisabled(true);
  }
  $('form').addEventListener('submit', submit);
  $('peek').addEventListener('click', peek);
  $('kbd').addEventListener('click', switchKeys);
  $('secret').addEventListener('input', () => { $('secret').removeAttribute('aria-invalid'); if (!$('secret').disabled) setMessage('', ''); });
  if (!noPin) $('secret').focus();
})();
