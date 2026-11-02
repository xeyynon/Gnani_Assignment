function problemCard(p) {
  const [cls, label] = severityView(p.severity);
  const open = h('a', { class: 'btn', href: '#edit/' + p.shop }, icon('edit'), 'Open shop');
  const solve = p.severity === 'error' ? null : h('button', { class: 'btn', type: 'button', text: 'Mark solved' });
  if (solve) solve.addEventListener('click', () => run(solve, $('problems-msg'), 'Marking solved...', async () => {
    await adminCall('dismiss', { id: p.id }); await refreshNow(); say($('problems-msg'), 'Marked solved. You can undo it below.', 'good');
  }));
  return h('div', { class: 'card problem' },
    h('div', { class: 'row' }, h('span', { class: 'who', text: p.title }), h('span', { class: 'pill ' + cls, text: label })),
    h('div', { class: 'muted', text: p.shop }),
    h('p', { text: p.detail }),
    h('div', { class: 'actions' }, open, solve),
    p.severity === 'error' ? h('div', { class: 'muted', text: 'An error cannot be marked solved: the shop cannot work until it is fixed.' }) : null);
}
function solvedCard(p) {
  const undo = h('button', { class: 'btn', type: 'button', text: 'Undo' });
  undo.addEventListener('click', () => run(undo, $('problems-msg'), 'Bringing it back...', async () => {
    await adminCall('restore', { id: p.id }); await refreshNow(); say($('problems-msg'), 'It is listed as a problem again.', 'good');
  }));
  return h('div', { class: 'card problem' },
    h('div', { class: 'row' }, h('span', { class: 'who', text: p.title }), undo),
    h('div', { class: 'muted', text: p.shop + (p.at ? ', marked solved ' + relTime(p.at) : '') + (p.note ? ': ' + p.note : '') }));
}
