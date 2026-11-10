/* ---- several calls at once: the label of each call's tab ('Call 2: Phone, 1:05'). Pure, so it is tested in Node. ---- */
function liveTabLabels(live) {
  return (Array.isArray(live) ? live : []).map((c, i) => {
    c = c || {};
    const word = c.channel === 'phone' ? 'Phone' : c.channel === 'browser' ? 'Browser' : '';
    const secs = c.seconds == null || c.seconds === '' ? NaN : Number(c.seconds);
    return 'Call ' + (i + 1) + [word, Number.isFinite(secs) ? callLength(secs) : ''].filter(Boolean).map((p, j) => (j ? ', ' : ': ') + p).join('');
  });
}
function liveSelection(current, count) {          // which call is being watched: the one picked, or the first when it is gone
  return Number.isInteger(current) && current >= 0 && current < count ? current : 0;
}
