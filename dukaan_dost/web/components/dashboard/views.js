/* ---- the sections: the side menu switches between views of one page, by the address fragment ---- */
const VIEWS = ['overview', 'orders', 'credit', 'loans'];
function showView(moveFocus) {
  const v = VIEWS.includes(location.hash.slice(1)) ? location.hash.slice(1) : 'overview';
  document.querySelectorAll('[data-page]').forEach(p => { p.hidden = p.dataset.page !== v; });
  document.querySelectorAll('.nav[data-view]').forEach(a => { if (a.dataset.view === v) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current'); });
  if (moveFocus) { const h2 = document.querySelector('[data-page="' + v + '"] h2[tabindex]'); if (h2) h2.focus(); }   // a keyboard user lands on the new section, not the old link
}
window.addEventListener('hashchange', () => showView(true));
document.querySelectorAll('[data-go]').forEach(b => b.addEventListener('click', () => { location.hash = b.dataset.go; }));
