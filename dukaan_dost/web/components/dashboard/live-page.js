/* ---- the Live view: the call that is on right now. The page asks every second while a call is on; a part is rebuilt only when it changed,
   so a bubble you are selecting is not thrown away each second. Nothing here is stored: it is drawn from the data feed and forgotten. ---- */
const liveSeen = {};
function liveChanged(name, value) {
  const k = JSON.stringify(value);
  if (liveSeen[name] === k) return false;
  liveSeen[name] = k; return true;
}
function liveBubble(l) { return h('div', { class: 'lmsg ' + l.who }, h('small', { text: l.who === 'agent' ? 'Agent' : 'Caller' }), h('span', { text: l.text })); }
let liveFollow = true;                                        // follow the newest line, until the reader scrolls up (the log cannot scroll while this view is hidden, so this is remembered, not measured)
$('livelog').addEventListener('scroll', () => { const e = $('livelog'); if (e.clientHeight) liveFollow = e.scrollHeight - e.scrollTop - e.clientHeight < 24; });
window.addEventListener('hashchange', () => { if (liveFollow && location.hash === '#live') $('livelog').scrollTop = $('livelog').scrollHeight; });
function renderLiveLog(lines) {
  const groups = groupLines(lines);
  if (!liveChanged('log', groups)) return;
  const el = $('livelog'), was = el.scrollTop;
  el.replaceChildren(...(groups.length ? groups.map(liveBubble) : [h('div', { class: 'empty', text: 'Nothing said yet.' })]));
  el.scrollTop = liveFollow ? el.scrollHeight : was;         // a reader who scrolled up is left where they are
}
function renderLiveOrder(o) {
  const v = liveOrder(o);
  if (!liveChanged('order', v)) return;
  if (!v || !v.items.length) { $('liveorder').replaceChildren(h('div', { class: 'empty', text: 'No items yet.' })); return; }
  const tb = h('tbody');
  v.items.forEach(i => tb.appendChild(h('tr', null, h('td', { text: i.name }), h('td', { class: 'q', text: i.qty }), h('td', { class: 'num', text: i.amount }))));
  $('liveorder').replaceChildren(h('table', null, tb), h('div', { class: 'lotal' }, h('span', { text: 'Total' }), h('span', { text: v.total })));
}
function renderLiveLoan(ev) {
  const v = loanView(ev);
  if (!liveChanged('loan', v)) return;
  $('liveloanbox').hidden = !v;
  if (!v) { $('liveloan').replaceChildren(); return; }
  const dl = h('dl', { class: 'loanrows' });
  v.rows.forEach(([k, val]) => { dl.appendChild(h('dt', { text: k })); dl.appendChild(h('dd', { class: val.startsWith('₹') ? 'amt' : '', text: val })); });
  const parts = [v.where ? h('div', { class: 'loanwhere', text: v.where }) : null, dl];
  if (v.emi) parts.push(h('div', { class: 'emi' }, h('div', { class: 'big', text: v.emi.amount + ' a month' }), h('div', { class: 'after', text: 'for ' + v.emi.months + ' months, ' + v.emi.after })));
  if (v.note) parts.push(h('p', { class: 'loannote', text: v.note }));
  parts.push(h('p', { class: 'loanfine', text: 'Indicative only. These figures come from the scheme terms this project uses, not from a bank or the government.' }));
  $('liveloan').replaceChildren(...parts.filter(Boolean));
}
function renderLive(live) {
  live = Array.isArray(live) ? live : [];
  const on = live.length > 0, c = on ? (live[0] || {}) : null;
  $('liveon').hidden = !on; $('liveempty').hidden = on;
  const nav = $('navlive'); nav.textContent = String(live.length); nav.hidden = !on;
  $('liveline').textContent = on ? liveHeading(c) + (live.length > 1 ? '. ' + live.length + ' calls are on; this shows the first.' : '') : 'No call is on right now.';
  if (!on) {                                                  // forget the last call, so the next one is drawn from scratch
    Object.keys(liveSeen).forEach(k => delete liveSeen[k]); liveFollow = true;
    $('livelog').replaceChildren(); $('liveorder').replaceChildren(); $('liveloan').replaceChildren(); $('liveloanbox').hidden = true;
    return;
  }
  renderLiveLog(c.lines); renderLiveOrder(c.order); renderLiveLoan(c.loan);
}
$('liveempty').replaceChildren(emptyCard(EMPTY.live));
