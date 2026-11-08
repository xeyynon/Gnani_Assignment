/* ---- a short first-visit tour: four steps, always skippable, replayable from the menu; Escape ends it ---- */
const TOUR_KEY = 'dd:tour';
let tourAt = -1, tourList = [], tourOpener = null;
function tourSeen() { try { return localStorage.getItem(TOUR_KEY) !== null; } catch (e) { return true; } }   // no storage: never start by itself, it would come back on every visit
function tourRemember() { try { localStorage.setItem(TOUR_KEY, '1'); } catch (e) {} }
function tourOpen() { return !$('tour').hidden; }
function tourVisible(el) {
  if (!el) return false;
  const r = el.getBoundingClientRect();
  return r.width > 0 && r.height > 0 && getComputedStyle(el).visibility !== 'hidden';
}
function placeTour() {
  const s = tourList[tourAt]; if (!s) return;
  const r = s.el.getBoundingClientRect(), ring = $('tour-ring'), tip = $('tour-tip'), pad = 4;
  ring.style.left = (r.left - pad) + 'px'; ring.style.top = (r.top - pad) + 'px';
  ring.style.width = (r.width + 2 * pad) + 'px'; ring.style.height = (r.height + 2 * pad) + 'px';
  const at = tourPlace({ left: r.left, top: r.top, right: r.right, bottom: r.bottom + pad, width: r.width, height: r.height },
    { w: document.documentElement.clientWidth, h: document.documentElement.clientHeight }, { w: tip.offsetWidth, h: tip.offsetHeight });
  tip.style.left = at.left + 'px'; tip.style.top = at.top + 'px'; tip.style.setProperty('--arrow', at.arrow + 'px'); tip.dataset.side = at.side;
}
function showTourStep(i) {
  const s = tourList[i]; tourAt = i;
  s.el.scrollIntoView({ block: 'nearest', inline: 'nearest' });
  $('tour-step').textContent = tourLabel(i, tourList.length);
  $('tour-title').textContent = s.title; $('tour-text').textContent = s.text;
  $('tour-next').textContent = i === tourList.length - 1 ? 'Done' : 'Next';
  placeTour();
  $('tour-tip').focus();                                     // focus moves into the tip, so a screen reader reads its title and text first
}
function startTour(opener) {
  if (document.documentElement.getAttribute('data-menu') === 'closed') setMenu(true, false);    // the steps point at the menu
  tourList = TOUR_STEPS.map(s => ({ ...s, el: document.querySelector(s.target) })).filter(s => tourVisible(s.el));
  if (tourList.length < 2) return;
  tourOpener = opener || null;
  $('tour').hidden = false;
  showTourStep(0);
}
function endTour() {
  $('tour').hidden = true; tourAt = -1; tourRemember();     // done or skipped, it is a choice: it does not start by itself again
  (tourOpener || $('tourbtn')).focus();                      // focus goes back to the button that replays the tour
}
function maybeStartTour() { if (!tourSeen() && !orderIdFromHash(location.hash)) startTour(null); }
$('tour-next').addEventListener('click', () => { if (tourAt + 1 < tourList.length) showTourStep(tourAt + 1); else endTour(); });
$('tour-skip').addEventListener('click', endTour);
$('tour-catch').addEventListener('click', endTour);
$('tourbtn').addEventListener('click', () => startTour($('tourbtn')));
document.addEventListener('keydown', e => {
  if (!tourOpen()) return;
  if (e.key === 'Escape') { e.preventDefault(); endTour(); return; }
  if (e.key === 'Tab') {                                     // Tab stays inside the tip: tip, Skip, Next
    const order = [$('tour-tip'), $('tour-skip'), $('tour-next')], i = order.indexOf(document.activeElement);
    e.preventDefault(); order[(i + (e.shiftKey ? order.length - 1 : 1)) % order.length].focus();
  }
});
window.addEventListener('resize', () => { if (tourOpen()) placeTour(); });
document.addEventListener('transitionend', () => { if (tourOpen()) placeTour(); }, true);      // the menu may still be sliding in when the tour opens it
window.addEventListener('scroll', () => { if (tourOpen()) placeTour(); }, true);
