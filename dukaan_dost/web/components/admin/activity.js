function activityCard(e) {
  const where = activityWhere(e, lastData ? lastData.shops : []);
  return h('div', { class: 'card' },
    h('div', { class: 'row' }, h('span', { class: 'who', text: activityLabel(e.kind) }), h('span', { class: 'muted', text: relTime(e.at) })),
    h('div', { class: 'muted', text: [where, e.detail].filter(Boolean).join(' - ') }));
}
