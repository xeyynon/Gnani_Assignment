const OVERVIEW_ROWS = 4;
function miniProblem(p) {
  const [cls, label] = severityView(p.severity);
  return h('div', { class: 'mini' }, h('span', { class: 'pill ' + cls, text: label }),
    h('div', { class: 'mt' }, h('div', { class: 'who', text: p.title }), h('div', { class: 'muted', text: p.shop })));
}
function miniActivity(e) {
  const where = activityWhere(e, lastData ? lastData.shops : []);
  return h('div', { class: 'mini' },
    h('div', { class: 'mt' }, h('div', { class: 'who', text: activityLabel(e.kind) }), h('div', { class: 'muted', text: [where, e.detail].filter(Boolean).join(' - ') })),
    h('span', { class: 'muted', text: relTime(e.at) }));
}
function renderOverviewPanels(d) {
  const problems = d.problems || [], activity = d.activity || [];
  fill('ov-problems', previewCount(problems, OVERVIEW_ROWS), miniProblem, 'Nothing is wrong with any shop.');
  fill('ov-activity', previewCount(activity, OVERVIEW_ROWS), miniActivity, 'Nothing has been changed from this page yet.');
  const link = (id, total, shown) => { const a = $(id); a.firstChild.textContent = viewAllText(total, shown); a.hidden = !total; };
  link('ov-problems-all', problems.length, OVERVIEW_ROWS);
  link('ov-activity-all', activity.length, OVERVIEW_ROWS);
}
