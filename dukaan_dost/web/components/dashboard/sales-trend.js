function renderTrend(days) {
  if (!trendHasData(days)) { $('trend').replaceChildren(h('div', { class: 'empty', text: 'No sales in the last 7 days yet.' })); $('trend').style.height = 'auto'; return; }
  $('trend').style.height = '';
  const max = Math.max(0, ...days.map(d => d.sales));
  $('trend').replaceChildren(...days.map((d, i) => h('div', { class: 'col' + (i === days.length - 1 ? ' today' : '') },
    h('span', { class: 'val', text: shortRupees(d.sales) }),
    h('div', { class: 'bar', style: 'height:' + barPercent(d.sales, max) * 0.72 + '%' }),
    h('span', { class: 'day', text: i === days.length - 1 ? 'Today' : fmtDate(d.date) }))));
  $('trend').setAttribute('aria-label', 'Sales for each of the last seven days: ' + days.map(d => fmtDate(d.date) + ' ' + rupees(d.sales)).join(', '));
}
