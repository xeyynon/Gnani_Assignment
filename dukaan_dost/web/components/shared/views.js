/* ---- the sections: a page is several views, shown one at a time by the address fragment ---- */
const VIEWS = [...new Set([...document.querySelectorAll('[data-page]')].map(p => p.dataset.page))];   // the first in the page is the default
function viewFromHash() {                     // '#edit/alpha' is the view 'edit' with the part 'alpha'
  const [name, ...rest] = location.hash.slice(1).split('/');
  return { name: VIEWS.includes(name) ? name : VIEWS[0], part: rest.join('/') };
}
function showView(moveFocus) {
  const v = viewFromHash().name;
  document.querySelectorAll('[data-page]').forEach(p => { p.hidden = p.dataset.page !== v; });
  document.querySelectorAll('.nav[data-view]').forEach(a => { if (a.dataset.view === v) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current'); });
  if (moveFocus) { const h2 = document.querySelector('[data-page="' + v + '"] h2[tabindex]'); if (h2) h2.focus(); }   // a keyboard user lands on the new section, not the old link
}
window.addEventListener('hashchange', () => showView(true));
document.querySelectorAll('[data-go]').forEach(b => b.addEventListener('click', () => { location.hash = b.dataset.go; }));
