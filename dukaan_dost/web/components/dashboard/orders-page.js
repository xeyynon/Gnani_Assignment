const openOrders = new Set();                  // the orders the shopkeeper opened: the list is redrawn every poll, and an open order must not snap shut
function orderCard(o) {
  const detail = h('div', null,
    h('table', null, h('tbody', null, ...o.items.map(i => h('tr', null,
      h('td', { text: i.name }), h('td', { text: i.qty != null ? i.qty + (i.unit ? ' ' + i.unit : '') : '' }), h('td', { class: 'num', text: rupees(i.line_total) }))))),
    o.payment === 'udhaar' && o.balance_after != null ? h('p', { class: 'muted', text: 'Credit balance ' + rupees(o.balance_before) + ' → ' + rupees(o.balance_after) }) : null,
    o.delivery ? h('p', { class: 'muted', text: 'Delivery: ' + o.delivery }) : null);
  const summary = h('summary', null,
    h('div', { class: 'row' }, h('span', { class: 'who', text: o.customer || 'Walk-in caller' }), h('span', { class: 'pill ' + o.status, text: statusLabel(o.status) })),
    h('div', { text: itemsSummary(o.items) }),
    h('div', { class: 'row' }, h('span', { class: 'muted', text: relTime(o.time) }),
      h('span', null, h('span', { class: 'pill pay' + (o.payment === 'udhaar' ? ' credit' : ''), text: paymentLabel(o.payment) }), ' ', h('span', { class: 'total', text: rupees(o.total) }))));
  const details = h('details', null, summary, detail);
  details.open = openOrders.has(o.id);
  details.addEventListener('toggle', () => { if (details.open) openOrders.add(o.id); else openOrders.delete(o.id); });
  return h('div', { class: 'card' + ((freshUntil[o.id] || 0) > Date.now() ? ' fresh' : ''), 'data-oid': o.id }, details);
}
