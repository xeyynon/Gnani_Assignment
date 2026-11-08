/* ---- keeping the page live: ask the server for the data every few seconds, say how fresh it is, say plainly when signed out ---- */
let lastOk = 0, signedOut = false, failed = false;
function tick() {
  const el = $('updated'), dot = $('dot');
  if (signedOut) return;
  if (!lastOk) { el.textContent = failed ? 'Could not load the data yet. Retrying...' : 'Loading...'; dot.className = 'dot' + (failed ? ' off' : ''); dot.textContent = failed ? 'Offline' : ''; return; }
  const s = Math.round((Date.now() - lastOk) / 1000);
  const stale = s > 10;
  dot.className = 'dot' + (stale ? ' off' : '');
  dot.textContent = stale ? 'Offline' : 'Live';                       // the word, not a colour alone (WCAG 1.4.1)
  el.textContent = stale ? 'Connection lost. Showing data from ' + s + ' s ago.' : 'Updated ' + (s < 2 ? 'just now' : s + ' s ago');
}
async function poll(url, draw, everyMs) {
  try {
    const r = await fetch(url, { cache: 'no-store', credentials: 'same-origin' });
    if (r.status === 401 || r.status === 429) {
      signedOut = true;
      $('updated').textContent = r.status === 401 ? 'Signed out.' : 'Too many wrong attempts. Try again in a minute.';
      $('dot').className = 'dot off';
      $('dot').textContent = 'Signed out';
      $('notices').replaceChildren(h('div', { class: 'banner bad' }, h('span', { class: 'nlabel', text: 'Signed out' }), 'Sign in again to see this shop. ', h('button', { type: 'button', id: 'reload', text: 'Sign in' })));
      $('reload').addEventListener('click', () => location.reload());
      return;
    }
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const data = await r.json();
    try {
      draw(data);
      lastOk = Date.now();
      failed = false;
    } catch (e) {                                   // a bug in drawing the data: say so, don't sit on "Loading..."
      console.error(e);
      $('notices').replaceChildren(h('div', { class: 'banner bad' }, h('span', { class: 'nlabel', text: 'Problem' }), 'The page could not show this data (' + e.message + ').'));
    }
  } catch (e) { failed = true; /* a network problem: keep the last data; tick() shows the connection warning */ }
  tick();
  setTimeout(() => poll(url, draw, everyMs), everyMs);
}
