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
