const has = v => v !== null && v !== undefined && v !== '';
function loanCard(l) {
  const body = l.covered === false
    ? h('p', { class: 'muted', text: 'Project cost ' + rupees(l.project_cost) + ' is above ₹50 lakh, so no scheme applies.' })
    : h('div', null,
        h('div', { text: rupees(l.margin_money) + ' margin → ' + rupees(l.project_cost) + ' project → ' + rupees(l.loan_amount) + ' loan' }),
        h('div', { class: 'muted', text: [has(l.scheme) ? l.scheme : null, has(l.annual_rate_pct) ? l.annual_rate_pct + '% a year' : null].filter(Boolean).join(', ') || 'Scheme not recorded' }),
        h('div', { class: 'total', text: rupees(l.monthly_instalment) + (has(l.repayment_months) ? ' × ' + l.repayment_months + ' months' : '') }),
        has(l.moratorium_months) ? h('div', { class: 'muted', text: 'after a ' + l.moratorium_months + '-month moratorium' }) : null);
  return h('div', { class: 'card' },
    h('div', { class: 'row' }, h('span', { class: 'who', text: [l.business, l.place].filter(Boolean).join(', ') || 'Loan enquiry' }), h('span', { class: 'tag', text: 'indicative' })),
    body, h('div', { class: 'muted', text: relTime(l.time) }));
}
