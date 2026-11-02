const nf = new Intl.NumberFormat('en-IN');
function rupees(n) { return '₹' + nf.format(Math.round(Number(n) || 0)); }
const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
function fmtDate(iso) {                       // 'YYYY-MM-DD' -> '28 Oct', without any time-zone shift
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || '');
  return m ? Number(m[3]) + ' ' + MONTHS[Number(m[2]) - 1] : '';
}
