function itemsSummary(items, max) {
  max = max || 3;
  const parts = (items || []).slice(0, max).map(i => (i.qty != null ? i.qty + (i.unit ? ' ' + i.unit : '') + ' ' : '') + i.name);
  const more = (items || []).length - max;
  return parts.join(', ') + (more > 0 ? ' +' + more + ' more' : '');
}
function callStatus(live) {                  // [{seconds}] -> the line shown at the top
  if (!live || !live.length) return 'No call right now';
  const s = live[0].seconds, t = Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0');
  return (live.length > 1 ? live.length + ' calls' : 'A customer is on a call') + ' (' + t + ')';
}
function limitUsed(balance, limit) { return limit > 0 ? Math.max(0, Math.min(1, balance / limit)) : 0; }
const STATUS = { confirmed: 'Confirmed', credit_pending: 'Credit pending', incomplete: 'Incomplete' };
function statusLabel(s) { return STATUS[s] || 'Confirmed'; }
function paymentLabel(p) { return { cash: 'Cash', upi: 'UPI', udhaar: 'On credit' }[p] || (p || ''); }
function change(now, before, label) {         // today against yesterday -> {text, dir}; no percentage from a zero
  label = label || 'vs yesterday';
  now = Number(now) || 0; before = Number(before) || 0;
  if (!before) return { text: now ? 'nothing yesterday' : 'no change', dir: '' };
  const pct = Math.round((now - before) / before * 100);
  if (!pct) return { text: 'same as yesterday', dir: '' };
  return { text: (pct > 0 ? '▲ +' : '▼ ') + pct + '% ' + label, dir: pct > 0 ? 'up' : 'down' };
}
function trendHasData(days) { return (days || []).some(d => Number(d.sales) > 0); }
function shortRupees(n) {                    // for labels above the bars
  n = Math.round(Number(n) || 0);
  return n >= 1000 ? '₹' + (n / 1000).toFixed(1).replace(/\.0$/, '') + 'k' : '₹' + n;
}
function barPercent(value, max) { return max > 0 ? Math.max(2, Math.round((Number(value) || 0) / max * 100)) : 2; }
function attention(orders, ledger) {         // what needs the shopkeeper, most urgent first
  const out = [];
  (orders || []).forEach(o => {
    if (o.status === 'incomplete') out.push({ kind: 'warn', title: (o.customer || 'Walk-in caller') + ': incomplete order', tag: rupees(o.total) });
    else if (o.status === 'credit_pending') out.push({ kind: 'amber', title: (o.customer || 'A caller') + ': credit pending', tag: rupees(o.total) });
  });
  (ledger || []).forEach(c => {
    if (limitUsed(c.balance, c.credit_limit) >= 0.9) out.push({ kind: 'warn', title: c.name + ': credit near the limit', tag: rupees(c.balance) + ' / ' + rupees(c.credit_limit) });
  });
  return out;
}
function callPageUrl(pathname) {                          // /s/<shop>/dashboard -> /s/<shop>/ : the shop's own call page ("/" when the address is not a shop's)
  const m = /^(\/s\/[^/]+\/)dashboard\/?$/.exec(String(pathname || ''));
  return m ? m[1] : '/';
}
/* ---- the Calls view: one card per ended call, from the counts-only record (call_stats.py) ---- */
const LANGUAGE_NAMES = { 'te-in': 'Telugu', 'hi-in': 'Hindi', 'en-in': 'English', 'hi-en': 'Hinglish', 'en-us': 'English' };
function languageName(code) { return LANGUAGE_NAMES[String(code || '').toLowerCase()] || ''; }
function callLength(seconds) {               // 192 -> '3:12'
  const s = Math.max(0, Math.round(Number(seconds) || 0));
  return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0');
}
function timesWord(n) { return n === 1 ? 'once' : n === 2 ? 'twice' : n + ' times'; }
function callOutcome(c) {                    // -> {text, cls}: what came of the call, as a pill
  if (c.outcome === 'ordered') {
    if (c.status === 'incomplete') return { text: 'Order incomplete', cls: 'incomplete' };
    if (c.status === 'credit_pending') return { text: 'Ordered, credit pending', cls: 'credit_pending' };
    return { text: 'Ordered', cls: 'confirmed' };
  }
  if (c.outcome === 'loan') return { text: 'Loan guidance', cls: 'loan' };
  return { text: 'No order', cls: 'none' };
}
function callMeta(c) {                       // 'Hindi · 3:12 · spoke 7 times'
  const n = Math.max(0, Number(c.turns) || 0);
  return [languageName(c.language), callLength(c.seconds), n ? 'spoke ' + timesWord(n) : 'nothing understood']
    .filter(Boolean).join(' · ');
}
function callNotes(c) {                      // what got in the way on this call, in plain words; [] when nothing did
  const out = [], n = k => Math.max(0, Number(c[k]) || 0);
  if (n('model_failures')) out.push({ kind: 'warn', text: 'The agent could not answer ' + timesWord(n('model_failures')) });
  if (n('no_speech')) out.push({ kind: '', text: 'Speech not caught ' + timesWord(n('no_speech')) });
  if (n('barge_ins')) out.push({ kind: '', text: 'Caller cut in ' + timesWord(n('barge_ins')) });
  return out;
}
function callsLine(summary) {                // the line under the Calls heading
  const today = Number((summary || {}).calls_today) || 0, all = Number((summary || {}).calls_total) || 0;
  return (today ? today + (today === 1 ? ' call' : ' calls') + ' today' : 'No calls yet today') + (all ? ', ' + all + ' in all' : '') + '.';
}
function orderLink(call, orders) {           // an ordered call -> '#orders/<id>' when that order is in the list the page has; otherwise null (no dead link)
  if (!call || call.outcome !== 'ordered' || !call.order_id) return null;
  return (orders || []).some(o => o.id === call.order_id) ? '#orders/' + call.order_id : null;
}
function orderIdFromHash(hash) {             // '#orders/20261107-215910-717' -> the id; anything else -> null
  const m = /^#orders\/([A-Za-z0-9_-]+)$/.exec(String(hash || ''));
  return m ? m[1] : null;
}
/* ---- onboarding: what an empty list says, and the steps of the first-visit tour ---- */
const EMPTY = {                              // a title that says what is missing, one sentence on what will appear, one way to start
  orders: { title: 'No orders yet', text: 'When a customer orders by phone, the order appears here within seconds of the call ending.', action: 'Try a call yourself' },
  ledger: { title: 'Nobody owes anything', text: 'A customer who buys on credit (udhaar) appears here with what they owe and their limit.' },
  loans: { title: 'No loan enquiries yet', text: 'When a caller asks about a business loan, the figures the agent quoted are kept here.', action: 'Try a call yourself' },
  calls: { title: 'No calls yet', text: 'Every call that ends is listed here, even when nothing was ordered.', action: 'Try a call yourself' },
};
const TOUR_STEPS = [                         // four steps, each on something the shopkeeper will use first
  { target: '#callpage', title: 'Try a call yourself', text: 'This opens the page your customers call from. Press Start call and order something, the way a customer would.' },
  { target: '.nav[data-view="orders"]', title: 'Orders arrive here', text: 'When a call ends with an order, it appears here within seconds, with what was bought and the total.' },
  { target: '.nav[data-view="calls"]', title: 'Every call is listed', text: 'Calls where nothing was ordered show here too, with what got in the way.' },
  { target: '#calls', title: 'A call in progress', text: 'While a customer is on a call, this bar says so and how long it has lasted.' },
];
function tourLabel(i, n) { return 'Step ' + (i + 1) + ' of ' + n; }
function tourPlace(rect, view, pop, gap) {   // where the tip goes: below the target, above it when there is no room below; always inside the window
  gap = gap == null ? 12 : gap;
  const m = 8;
  const below = rect.bottom + gap + pop.h <= view.h - m, above = rect.top - gap - pop.h >= m;
  const side = below || !above ? 'below' : 'above';
  let top = side === 'below' ? rect.bottom + gap : rect.top - gap - pop.h;
  top = Math.max(m, Math.min(top, view.h - pop.h - m));
  const left = Math.max(m, Math.min(rect.left, view.w - pop.w - m));
  const arrow = Math.max(14, Math.min(rect.left + rect.width / 2 - left, pop.w - 14));      // where the tip's pointer sits along its edge
  return { left, top, arrow, side };
}
