/* ---- the live transcript ---- */
let thinkingEl = null, lastAgent = null;
function scrollDown() { const t = $('transcript'); if ($('autoscroll').checked) t.scrollTop = t.scrollHeight; }
function addMsg(role, text, replyId) {
  const e = $('talkempty'); if (e) e.remove();
  const m = h('div', 'msg ' + role);
  m.appendChild(h('small', null, role === 'user' ? 'You' : 'Dukaan Dost'));
  m.appendChild(h('span', null, text));
  if (replyId != null) m.dataset.reply = replyId;
  if (thinkingEl) $('transcript').insertBefore(m, thinkingEl); else $('transcript').appendChild(m);
  scrollDown();
  return m;
}
function showThinking(on) {
  if (on && !thinkingEl) { thinkingEl = h('div', 'dots'); for (let i = 0; i < 3; i++) thinkingEl.appendChild(h('i')); $('transcript').appendChild(thinkingEl); scrollDown(); }
  if (!on && thinkingEl) { thinkingEl.remove(); thinkingEl = null; }
}
function agentSaid(replyId, text) {                      // sentences of one reply share a bubble
  if (lastAgent && lastAgent.dataset.reply === String(replyId) && lastAgent.isConnected) {
    lastAgent.lastChild.textContent += ' ' + text; scrollDown();
  } else lastAgent = addMsg('agent', text, replyId);
}
function resetTranscript() {
  const empty = h('div', 'empty', 'What you and the agent say appears here.'); empty.id = 'talkempty';
  $('transcript').replaceChildren(empty);
  thinkingEl = null; lastAgent = null;
}
