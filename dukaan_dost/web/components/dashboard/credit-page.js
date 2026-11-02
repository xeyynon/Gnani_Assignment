function ledgerRow(c) {
  const used = limitUsed(c.balance, c.credit_limit);
  const extra = c.promise_date ? 'Promised ' + fmtDate(c.promise_date) : (c.last_purchase ? 'Last bought ' + fmtDate(c.last_purchase) : '');
  return h('div', { class: 'card' },
    h('div', { class: 'row' }, h('span', { class: 'who', text: c.name }), h('span', { class: 'total', text: rupees(c.balance) })),
    h('div', { class: 'meter' + (used >= 0.9 ? ' high' : '') }, h('i', { style: 'width:' + Math.round(used * 100) + '%' })),
    h('div', { class: 'row' }, h('span', { class: 'muted', text: 'limit ' + rupees(c.credit_limit) }), h('span', { class: 'muted', text: extra })));
}
