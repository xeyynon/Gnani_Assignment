function loanCard(l) {
  const body = l.covered === false
    ? h('p', { class: 'muted', text: 'Project cost ' + rupees(l.project_cost) + ' is above ₹50 lakh, so no scheme applies.' })
    : h('div', null,
        h('div', { text: rupees(l.margin_money) + ' margin → ' + rupees(l.project_cost) + ' project → ' + rupees(l.loan_amount) + ' loan' }),
        h('div', { class: 'muted', text: l.scheme + ', ' + l.annual_rate_pct + '% a year' }),
        h('div', { class: 'total', text: rupees(l.monthly_instalment) + ' × ' + l.repayment_months + ' months' }),
        h('div', { class: 'muted', text: 'after a ' + l.moratorium_months + '-month moratorium' }));
  return h('div', { class: 'card' },
    h('div', { class: 'row' }, h('span', { class: 'who', text: [l.business, l.place].filter(Boolean).join(', ') || 'Loan enquiry' }), h('span', { class: 'tag', text: 'indicative' })),
    body, h('div', { class: 'muted', text: relTime(l.time) }));
}
