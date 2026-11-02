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
