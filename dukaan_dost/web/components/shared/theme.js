/* ---- the theme: Auto follows the device; Light and Dark are remembered on this browser ---- */
function readTheme() {                      // what was chosen here; before any choice, the page's own default (the admin starts dark), else follow the device
  try { const t = localStorage.getItem('dd:theme'); if (t === 'light' || t === 'dark' || t === 'auto') return t; } catch (e) {}
  return window.DD_DEFAULT_THEME === 'dark' || window.DD_DEFAULT_THEME === 'light' ? window.DD_DEFAULT_THEME : 'auto';
}
function showTheme(t) {
  const b = $('themebtn');
  b.querySelector('use').setAttribute('href', '#i-theme-' + t);
  b.querySelector('span').textContent = themeLabel(t);
  b.setAttribute('aria-label', 'Theme: ' + themeLabel(t) + '. Press to switch to ' + themeLabel(nextTheme(t)) + '.');
  b.title = 'Theme: ' + themeLabel(t) + ' (T)';
}
function setTheme(t) {
  const r = document.documentElement;
  if (t === 'auto') r.removeAttribute('data-theme'); else r.setAttribute('data-theme', t);
  try { localStorage.setItem('dd:theme', t); } catch (e) {}           // 'auto' is stored too, so it is a choice and not the same as never having chosen
  showTheme(t);
}
$('themebtn').addEventListener('click', () => setTheme(nextTheme(readTheme())));
document.addEventListener('keydown', e => { if (isPlainKey(e) && e.key.toLowerCase() === 't') $('themebtn').click(); });
showTheme(readTheme());
