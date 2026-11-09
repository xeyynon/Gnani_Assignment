const LANGS = { 'te-in': 'Telugu', 'hi-in': 'Hindi', 'en-in': 'English', 'hi-en': 'Hinglish', 'en-us': 'English' };
function langName(code) {                     // 'hi-IN' -> 'Hindi'; '' for anything unknown
  const k = String(code || '').toLowerCase();
  return LANGS[k] || LANGS[k.slice(0, 2) + '-in'] || '';
}
function clock(sec) { sec = Math.max(0, Math.floor(sec)); return Math.floor(sec / 60) + ':' + String(sec % 60).padStart(2, '0'); }
function barHeight(level, i, count, t) {      // one bar of the waveform: a bell-shaped envelope with a gentle wobble
  const env = Math.sin(Math.PI * (i + 0.5) / count), wob = 0.55 + 0.45 * Math.sin(t / 140 + i * 1.7);
  return 4 + Math.max(0, Math.min(1, level)) * 52 * env * wob;
}
