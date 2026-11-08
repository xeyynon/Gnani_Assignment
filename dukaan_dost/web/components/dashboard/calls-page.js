function callCard(c) {
  const out = callOutcome(c), notes = callNotes(c);
  return h('div', { class: 'card' },
    h('div', { class: 'row' }, h('span', { class: 'who', text: c.channel === 'phone' ? 'Phone call' : 'Browser call' }), h('span', { class: 'pill ' + out.cls, text: out.text })),
    h('div', { class: 'muted', text: callMeta(c) }),
    notes.length ? h('div', { class: 'notes' }, ...notes.map(x => h('span', { class: 'pill note' + (x.kind ? ' ' + x.kind : ''), text: x.text }))) : null,
    h('div', { class: 'row' }, h('span', { class: 'muted', text: relTime(c.time) }), c.total != null ? h('span', { class: 'total', text: rupees(c.total) }) : null));
}
function renderCalls(calls, summary) {
  $('callsline').textContent = callsLine(summary);
  const nav = $('navcalls'), today = Number((summary || {}).calls_today) || 0;
  nav.textContent = String(today); nav.hidden = !today;
  fill('callslist', calls, callCard, 'No calls yet. Each call shows here when it ends, even if nothing was ordered.');
}
