const nf = new Intl.NumberFormat('en-IN');
function rupees(n) { return '₹' + nf.format(Math.round(Number(n) || 0)); }
const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
function fmtDate(iso) {                       // 'YYYY-MM-DD' -> '28 Oct', without any time-zone shift
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || '');
  return m ? Number(m[3]) + ' ' + MONTHS[Number(m[2]) - 1] : '';
}
function relTime(iso, now) {
  const t = new Date(iso), n = now || new Date();
  if (isNaN(t)) return '';
  const mins = Math.round((n - t) / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return mins + ' min ago';
  const clock = t.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
  if (t.toDateString() === n.toDateString()) return Math.round(mins / 60) + ' h ago, ' + clock;
  const y = new Date(n); y.setDate(n.getDate() - 1);
  if (t.toDateString() === y.toDateString()) return 'yesterday ' + clock;
  return t.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' }) + ' ' + clock;
}
function greeting(hour) { return hour < 12 ? 'Good morning!' : hour < 17 ? 'Good afternoon!' : 'Good evening!'; }
