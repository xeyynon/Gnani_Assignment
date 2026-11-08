/* ---- '#orders/<id>': open that order and bring it into view (the Calls view links here) ---- */
function jumpToOrder() {
  const id = orderIdFromHash(location.hash);
  if (!id) return;
  openOrders.add(id);
  const card = document.querySelector('[data-oid="' + id + '"]');
  if (!card) return;                                           // not drawn yet: the first render calls this again
  card.querySelector('details').open = true;
  card.classList.add('fresh');                                 // the green edge says which one it is, until the next redraw
  card.scrollIntoView({ block: 'center' });
}
window.addEventListener('hashchange', jumpToOrder);
