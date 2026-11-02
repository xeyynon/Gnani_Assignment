/* ---- the side menu can be hidden: it slides out to the left, and a button in the top bar brings it back ---- */
function readMenu() { try { return menuOpen(localStorage.getItem('dd:menu')); } catch (e) { return true; } }
function setMenu(open, moveFocus) {
  const r = document.documentElement;
  if (open) r.removeAttribute('data-menu'); else r.setAttribute('data-menu', 'closed');
  try { if (open) localStorage.removeItem('dd:menu'); else localStorage.setItem('dd:menu', 'closed'); } catch (e) {}
  $('menuhide').setAttribute('aria-expanded', String(open));
  $('menushow').setAttribute('aria-expanded', String(open));
  if (moveFocus) (open ? $('menuhide') : $('menushow')).focus();      // focus goes to the button that replaces the one just pressed
}
$('menuhide').addEventListener('click', () => setMenu(false, true));
$('menushow').addEventListener('click', () => setMenu(true, true));
document.addEventListener('keydown', e => { if (isPlainKey(e) && e.key.toLowerCase() === 'b') setMenu(!readMenu(), true); });
setMenu(readMenu(), false);
