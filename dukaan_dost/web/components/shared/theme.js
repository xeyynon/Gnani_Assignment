/* ---- the theme: Auto follows the device; Light and Dark are remembered on this browser ---- */
function readTheme() { try { const t = localStorage.getItem('dd:theme'); return t === 'light' || t === 'dark' ? t : 'auto'; } catch (e) { return 'auto'; } }
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
  try { if (t === 'auto') localStorage.removeItem('dd:theme'); else localStorage.setItem('dd:theme', t); } catch (e) {}
  showTheme(t);
}
$('themebtn').addEventListener('click', () => setTheme(nextTheme(readTheme())));
document.addEventListener('keydown', e => { if (isPlainKey(e) && e.key.toLowerCase() === 't') $('themebtn').click(); });
showTheme(readTheme());
