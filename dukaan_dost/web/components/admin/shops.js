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
      link('/s/' + s.name + '/', null, 'Call page')));
}
