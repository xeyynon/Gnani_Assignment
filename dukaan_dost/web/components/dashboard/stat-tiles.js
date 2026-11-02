function tile(iconName, tone, key, value, sub, subCls, cls) {
  return h('div', { class: 'tile' + (cls ? ' ' + cls : '') },
    h('div', { class: 'ico ' + tone }, icon(iconName)),
    h('div', null, h('div', { class: 'k', text: key }), h('div', { class: 'v', text: value }), sub ? h('div', { class: 's' + (subCls ? ' ' + subCls : ''), text: sub }) : null));
}
function renderTiles(s) {
  const same = s.orders_yesterday_same_time != null;             // older servers only know the whole of yesterday
  const o = change(s.orders_today, same ? s.orders_yesterday_same_time : s.orders_yesterday, same ? 'vs this time yesterday' : 'vs yesterday');
  const m = change(s.sales_today, same ? s.sales_yesterday_same_time : s.sales_yesterday, same ? 'vs this time yesterday' : 'vs yesterday');
  $('tiles').replaceChildren(
    tile('cart', 'green', 'Orders today', String(s.orders_today), o.text, o.dir),
    tile('rupee', 'blue', 'Sales today', rupees(s.sales_today), m.text, m.dir, 'hero brut'),
    tile('users', 'credit', 'Owed on credit', rupees(s.udhaar_outstanding), s.customers_owing + (s.customers_owing === 1 ? ' customer' : ' customers')));
}
