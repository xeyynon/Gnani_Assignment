/* ---- the loan quote so far (read-only: the agent works it out and says it; this shows what was said, and that it is indicative) ---- */
const LOAN_EMPTY = 'Ask about a business loan and the figures appear here.';
function renderLoan(ev) {
  const v = loanView(ev);
  if (!v) return;                                                     // an event with no figures changes nothing
  const dl = h('dl', 'loanrows');
  v.rows.forEach(([k, val]) => { dl.appendChild(h('dt', null, k)); dl.appendChild(h('dd', val.startsWith('₹') ? 'amt' : null, val)); });
  const parts = [v.where ? h('div', 'loanwhere', v.where) : null, dl];
  if (v.emi) parts.push(h('div', 'emi', h('div', 'big', v.emi.amount + ' a month'), h('div', 'after', 'for ' + v.emi.months + ' months, ' + v.emi.after)));
  if (v.note) parts.push(h('p', 'loannote', v.note));
  parts.push(h('p', 'loanfine', 'Indicative only. These figures come from the scheme terms this project uses, not from a bank or the government.'));
  $('loan').replaceChildren(...parts.filter(Boolean));
}
function resetLoan() { $('loan').replaceChildren(h('div', 'empty', LOAN_EMPTY)); }
