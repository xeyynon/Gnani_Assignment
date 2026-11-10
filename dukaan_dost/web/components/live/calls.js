/* ---- several calls at once: one tab per call, and the shopkeeper picks which one to watch. With one call there is no tab bar.
   A tab is updated in place each second (its length changes), not rebuilt, so a tab you have focused stays focused. ---- */
let liveSel = 0;
function renderLiveTabs(live) {
  const bar = $('livetabs'), labels = liveTabLabels(live);
  liveSel = liveSelection(liveSel, labels.length);
  $('livecount').textContent = labels.length > 1 ? labels.length + ' calls on' : '';
  bar.hidden = labels.length < 2;
  if (labels.length < 2) { bar.replaceChildren(); return; }
  if (bar.children.length !== labels.length) {
    bar.replaceChildren(...labels.map((t, i) => h('button', { type: 'button', role: 'tab', 'data-i': i })));
  }
  labels.forEach((t, i) => {
    const b = bar.children[i], on = i === liveSel;
    b.textContent = t;
    b.className = 'livetab' + (on ? ' on' : '');
    b.setAttribute('aria-selected', String(on));
  });
}
$('livetabs').addEventListener('click', e => {
  const b = e.target.closest('button[data-i]');
  if (!b) return;
  liveSel = Number(b.getAttribute('data-i'));
  if (lastLive) drawLive(lastLive);                 // draw the call just picked now, not on the next poll
});
let lastLive = null;
function drawLive(live) {
  lastLive = live;
  renderLiveTabs(live);
  renderLive(live.length ? [live[liveSel]] : []);   // the shared Live drawing watches one call: hand it the one picked
}
