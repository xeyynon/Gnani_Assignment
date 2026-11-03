const LANGS = { 'te-in': 'Telugu', 'hi-in': 'Hindi', 'en-in': 'English', 'hi-en': 'Hinglish', 'en-us': 'English' };
function langName(code) {                     // 'hi-IN' -> 'Hindi'; '' for anything unknown
  const k = String(code || '').toLowerCase();
  return LANGS[k] || LANGS[k.slice(0, 2) + '-in'] || '';
}
function clock(sec) { sec = Math.max(0, Math.floor(sec)); return Math.floor(sec / 60) + ':' + String(sec % 60).padStart(2, '0'); }
function barHeight(level, i, count, t) {      // one bar of the waveform: a bell-shaped envelope with a gentle wobble
  const env = Math.sin(Math.PI * (i + 0.5) / count), wob = 0.55 + 0.45 * Math.sin(t / 140 + i * 1.7);
  return 4 + Math.max(0, Math.min(1, level)) * 52 * env * wob;
}

/* The loan quote the agent sends as {type: 'loan', ...}. Every figure is the calculator's, worked out on the server; the page
   only lays them out and never adds, rates or rounds anything itself. Returns null when the event carries no usable figures. */
function money(n) { return Number.isFinite(n) ? rupees(n) : ''; }
function loanView(ev) {
  if (!ev || !Number.isFinite(ev.project_cost)) return null;
  const where = [ev.business, ev.place].filter(s => typeof s === 'string' && s).join(', ');
  const rows = [['Project cost', money(ev.project_cost)]];
  if (Number.isFinite(ev.margin_money)) rows.push(['Your margin money', money(ev.margin_money)]);
  if (ev.covered === false || !ev.scheme || !Number.isFinite(ev.loan_amount)) {
    return { where, covered: false, rows, emi: null, note: 'A project this big is above what the scheme covers, so no scheme applies.' };
  }
  rows.push(['Loan', money(ev.loan_amount)]);
  rows.push(['Scheme', ev.scheme + (Number.isFinite(ev.annual_rate_pct) ? ', ' + ev.annual_rate_pct + '% a year' : '')]);
  if (Number.isFinite(ev.total_interest)) rows.push(['Total interest', money(ev.total_interest)]);
  const emi = Number.isFinite(ev.monthly_instalment) && Number.isFinite(ev.repayment_months) ? {
    amount: money(ev.monthly_instalment),
    months: ev.repayment_months,
    after: ev.moratorium_months > 0 ? 'after a ' + ev.moratorium_months + '-month moratorium' : 'no moratorium'
  } : null;
  const capped = Number.isFinite(ev.own_contribution) && Number.isFinite(ev.margin_money) && ev.own_contribution > ev.margin_money;
  return { where, covered: true, rows, emi, note: capped ? 'The loan is capped, so you put in ' + money(ev.own_contribution) + '.' : '' };
}
