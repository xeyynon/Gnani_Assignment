function shopCard(s) {
  const [cls, label] = stateView(s.state);
  const badges = h('div', { class: 'badges' },
    s.has_pin ? null : h('span', { class: 'tag', text: 'no PIN' }),
    s.live.length ? h('span', { class: 'chip on' }, h('span', { class: 'dot' }), liveText(s.live)) : null,
    s.problems ? h('span', { class: 'tag', text: plural(s.problems, 'problem', 'problems') }) : null);
  const link = (href, icon, text, extra) => h('a', { class: 'btn' + (extra ? ' ' + extra : ''), href }, icon ? icon : null, text);
  return h('div', { class: 'card shoprow' },
    h('div', { class: 'head' },
      h('div', { class: 'row' }, h('span', { class: 'who', text: s.title }), h('span', { class: 'pill ' + cls, text: label })),
      h('div', { class: 'muted', text: '/s/' + s.name + '/' }), badges),
    h('div', null, h('span', { class: 'lbl', text: 'Orders today' }), h('span', { class: 'num', text: String(s.orders_today) })),
    h('div', null, h('span', { class: 'lbl', text: 'Last order' }), h('span', { text: s.last_order ? relTime(s.last_order) : 'no orders yet' })),
    h('div', { class: 'actions' },
      link('#edit/' + s.name, icon('edit'), 'Edit', 'primary'),
      link('/s/' + s.name + '/dashboard', null, 'Shop dashboard'),
      link('/s/' + s.name + '/', null, 'Call page'),
      copyButton(s)));
}

let lastData = null, shopFilter = 'all', shopQuery = '';
function renderShops() {                    // the shops that match the tab and the search; the tabs show how many each would give
  if (!lastData) return;
  const counts = filterCounts(lastData.shops);
  document.querySelectorAll('.tab[data-filter]').forEach(b => {
    b.setAttribute('aria-pressed', String(b.dataset.filter === shopFilter));
    b.querySelector('.tc').textContent = String(counts[b.dataset.filter]);
  });
  fill('shops', filterShops(lastData.shops, shopFilter, shopQuery), shopCard, emptyShopsText(shopFilter, shopQuery, lastData.shops.length));
}
document.querySelectorAll('.tab[data-filter]').forEach(b => b.addEventListener('click', () => { shopFilter = b.dataset.filter; renderShops(); }));

/* ---- search: filters the shops; Ctrl+K or Cmd+K goes to it from anywhere; Escape clears it ---- */
$('searchkey').textContent = searchHint(navigator.platform);
$('search').addEventListener('input', () => {
  shopQuery = $('search').value;
  if (viewFromHash().name !== 'overview') location.hash = '#overview';          // the shops are on the overview
  renderShops();
});
$('search').addEventListener('keydown', e => { if (e.key === 'Escape') { $('search').value = ''; shopQuery = ''; renderShops(); $('search').blur(); } });
document.addEventListener('keydown', e => { if (isSearchKey(e)) { e.preventDefault(); $('search').focus(); $('search').select(); } });

function copyButton(s) {                    // copies the full call link, so it can be sent to a shopkeeper
  const b = h('button', { class: 'btn', type: 'button', 'aria-label': 'Copy the call link for ' + s.title }, icon('link'), 'Copy call link');
  b.addEventListener('click', async () => {
    const url = callLink(location.origin, s.name), msg = $('shops-msg');
    try { await navigator.clipboard.writeText(url); say(msg, 'Copied: ' + url, 'good'); }
    catch (e) { say(msg, 'Could not copy automatically. The link is ' + url, 'bad'); }          // no clipboard (not https, or blocked): show it instead
  });
  return b;
}
