/* ---- the order so far (read-only: the caller changes it by voice, and totals are computed on the server) ---- */
function renderOrder(o) {
  const items = (o && o.items) || [];
  $('ordertag').hidden = true;
  if (!items.length) { $('order').replaceChildren(h('div', 'empty', 'Nothing in the order yet.')); return; }
  const tb = h('tbody');
  items.forEach(i => {
    const tr = h('tr');
    tr.appendChild(h('td', null, i.name));
    tr.appendChild(h('td', 'q', i.qty != null ? i.qty + (i.unit ? ' ' + i.unit : '') : ''));
    tr.appendChild(h('td', 'num', i.line_total != null ? rupees(i.line_total) : ''));
    tb.appendChild(tr);
  });
  const tot = h('div', 'order-total'); tot.appendChild(h('span', null, 'Total')); tot.appendChild(h('span', null, rupees(o.total)));
  const table = h('table'); table.appendChild(tb);
  $('order').replaceChildren(table, tot);
}
function resetOrder() {
  $('order').replaceChildren(h('div', 'empty', 'Items you order are listed here with a running total.'));
  $('ordertag').hidden = false;
}
