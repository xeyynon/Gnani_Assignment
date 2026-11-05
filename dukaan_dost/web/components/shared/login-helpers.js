/* ---- the sign-in page's pure helpers: what to say, and how to send the PIN (tested in Node, no page needed) ---- */
function credentialHeader(user, secret) {                    // the same header a script sends; UTF-8 safe, so a PIN may use any characters
  const bytes = new TextEncoder().encode(user + ':' + secret);
  let bin = '';
  bytes.forEach(b => { bin += String.fromCharCode(b); });
  return 'Basic ' + btoa(bin);
}
function clock(sec) {                                         // 42 -> "0:42", 125 -> "2:05"
  const s = Math.max(0, Math.ceil(Number(sec) || 0));
  return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0');
}
function triesText(n) { return n === 1 ? '1 try left' : n + ' tries left'; }
function lockText(sec) { return 'Too many wrong tries. You can try again in ' + clock(sec) + '.'; }
function whatWord(kind) { return kind === 'admin' ? 'password' : 'PIN'; }
function loginOutcome(status, data, kind) {                    // the server's answer -> what the page does and says
  const what = whatWord(kind), d = data && typeof data === 'object' ? data : {};
  if (status === 200 && d.ok) return { kind: 'ok', text: 'Signed in. Opening the page...' };
  if (status === 429 || d.locked) { const wait = Number(d.retry_after) > 0 ? Number(d.retry_after) : 60; return { kind: 'locked', wait, text: lockText(wait) }; }
  if (d.wrong) return { kind: 'wrong', text: 'That ' + what + ' is not right.' + (Number.isInteger(d.remaining) && d.remaining > 0 ? ' ' + triesText(d.remaining) + '.' : '') };
  if (d.empty || status === 400) return { kind: 'empty', text: 'Enter your ' + what + '.' };
  if (status === 0) return { kind: 'error', text: 'Could not reach the server. Check the connection and try again.' };
  return { kind: 'error', text: 'Something went wrong (' + status + '). Try again.' };
}
function loginWords(kind, noPin) {                             // the fixed words of the page, by who is signing in
  if (kind === 'admin') return { sub: 'to the admin page', label: 'Admin password', placeholder: 'Admin password', help: 'This page is for the person who runs Dukaan Dost.', back: false, admin: false };
  return { sub: 'to your shop dashboard', label: 'Shop PIN', placeholder: 'Enter your PIN', back: true, admin: true,
    help: noPin ? '' : 'Forgot your PIN? Ask whoever set up your shop. They can set a new one from the admin page.' };
}
