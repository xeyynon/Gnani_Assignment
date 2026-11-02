/* ---- the notice at the top of the overview: dismissed until the numbers change ---- */
function storedBanner() { try { return localStorage.getItem('dd:admin-banner'); } catch (e) { return null; } }
function renderBanner(d) {
  const view = bannerView(d.totals, d.shops), box = $('adminbanner');
  box.dataset.key = view ? view.key : '';
  box.hidden = bannerHidden(view, storedBanner());
  if (view) { $('bn-title').textContent = view.title; $('bn-sub').textContent = view.sub; }
}
$('bn-x').addEventListener('click', () => {
  try { localStorage.setItem('dd:admin-banner', $('adminbanner').dataset.key); } catch (e) {}
  $('adminbanner').hidden = true;
  $('h-shops').focus();                                                  // focus goes to the panel below, not to the page body
});
