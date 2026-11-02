function recentRow(o) {
  const fresh = (freshUntil[o.id] || 0) > Date.now();
  return h('div', { class: 'orow' + (fresh ? ' fresh' : '') },
    h('span', { class: 'c-time muted', text: relTime(o.time) }),
    h('span', { class: 'c-who who', text: o.customer || 'Walk-in caller' }),
    h('span', { class: 'c-items', text: itemsSummary(o.items, 2) }),
    h('span', { class: 'c-total num total', text: rupees(o.total) }),
    h('span', { class: 'c-status' }, h('span', { class: 'pill ' + o.status, text: statusLabel(o.status) })));
}
function renderRecent(orders) {
  if (!orders.length) { $('recent').replaceChildren(h('div', { class: 'empty', text: 'No orders yet. They appear here within seconds of a call ending.' })); return; }
  const head = h('div', { class: 'orow head' }, h('span', { text: 'When' }), h('span', { text: 'Customer' }), h('span', { text: 'Order' }), h('span', { class: 'num', text: 'Total' }), h('span', { text: 'Status' }));
  $('recent').replaceChildren(head, ...orders.slice(0, 5).map(recentRow));
}
