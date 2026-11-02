/* ---- the waveform: the caller's own microphone while listening, the agent's voice while it speaks ---- */
const bars = [];
for (let i = 0; i < BARS; i++) { const b = h('i'); bars.push(b); $('level').appendChild(b); }
const buf = new Float32Array(512);
function voiceLevel() {
  if (!analyser) return 0;
  analyser.getFloatTimeDomainData(buf);
  let s = 0; for (let i = 0; i < buf.length; i++) s += buf[i] * buf[i];
  return Math.min(1, Math.sqrt(s / buf.length) * 5);
}
function frame(t) {
  const v = view();
  const target = !inCall ? 0 : v === 'speaking' ? voiceLevel() : v === 'listening' ? micLevel : 0;
  shownLevel += (target - shownLevel) * 0.35;
  for (let i = 0; i < BARS; i++) bars[i].style.height = barHeight(shownLevel, i, BARS, t) + 'px';
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);
