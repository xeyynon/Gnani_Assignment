// A real browser walks through the sign-in page. Run each flow on a FRESH server (it uses up wrong guesses):
//   FLOW=shop|admin SNAP_PIN=<shop pin> SNAP_ADMIN_PASSWORD=<admin password> SHOT=<folder for screenshots, optional> \
//     node --experimental-websocket scripts/ui_check/drive.mjs <page url> scripts/ui_check/flows/login.mjs 390 844 light
// The page url is the shop's dashboard (/s/<shop>/dashboard) for FLOW=shop and /admin for FLOW=admin. Browser is signed out at the start.
const flow = process.env.FLOW || 'shop';
const secret = flow === 'admin' ? process.env.SNAP_ADMIN_PASSWORD : process.env.SNAP_PIN;
const shot = name => process.env.SHOT ? `${process.env.SHOT}/${flow}-${name}.png` : undefined;
const what = flow === 'admin' ? 'password' : 'PIN';
const dataUrl = flow === 'admin' ? '/admin/data' : location_data();
function location_data() { return '/s/demo_kirana/dashboard/data'; }
const WAIT = 'const wait = ms => new Promise(r => setTimeout(r, ms));';
const fill = v => `${WAIT} const i = document.getElementById('secret'); i.value = ${JSON.stringify(v)}; document.getElementById('form').requestSubmit(); await wait(900);`;

export const steps = [
  { name: 'signed out, the sign-in page shows, not a browser prompt', js: `return [document.getElementById('login') !== null, document.querySelector('h1').textContent]`, expect: [true, 'Sign in'], shot: shot('1-idle') },
  { name: 'the PIN field is focused', js: `return document.activeElement.id`, expect: 'secret' },
  { name: 'an empty submit asks for the ' + what, js: `${WAIT} document.getElementById('form').requestSubmit(); await wait(300); return document.getElementById('msg').textContent`, expect: `Enter your ${what}.`, shot: shot('2-empty') },
  { name: 'a wrong ' + what + ' says so and how many tries are left', js: `${fill('0000wrong')} return document.getElementById('msg').textContent`, expect: `That ${what} is not right. 4 tries left.`, shot: shot('3-wrong') },
  { name: 'the field is marked invalid for a screen reader', js: `return document.getElementById('secret').getAttribute('aria-invalid')`, expect: 'true' },
  { name: 'the show button reveals the ' + what + ' and says so', js: `document.getElementById('peek').click(); const i = document.getElementById('secret'); return [i.type, document.getElementById('peek').getAttribute('aria-pressed')]`, expect: ['text', 'true'] },
  { name: 'while signed out the data is refused, with no browser prompt header', js: `const r = await fetch(${JSON.stringify(dataUrl)}, { cache: 'no-store' }); return [r.status, r.headers.get('www-authenticate')]`, expect: [401, null] },
  { name: 'the right ' + what + ' is sent', js: `const i = document.getElementById('secret'); i.value = ${JSON.stringify(secret)}; document.getElementById('form').requestSubmit(); return 'sent'`, expect: 'sent' },     // the page reloads: nothing may wait inside this step
  { name: 'and the real page opens, with a sign-out button', js: `${WAIT} await wait(2500); return [document.getElementById('login') === null, document.getElementById('signout') !== null]`, expect: [true, true], shot: shot('4-signed-in') },
  { name: 'the page can read its data with the session cookie alone', js: `const r = await fetch(${JSON.stringify(dataUrl)}, { cache: 'no-store' }); return r.status`, expect: 200 },
  { name: 'the cookie cannot be read by a script', js: `return document.cookie.includes('dd_session')`, expect: false },
  { name: 'sign out is pressed', js: `document.getElementById('signout').click(); return 'sent'`, expect: 'sent' },
  { name: 'and the sign-in page is back', js: `${WAIT} await wait(2500); return document.getElementById('login') !== null`, expect: true },
  { name: 'after signing out the data is refused again', js: `const r = await fetch(${JSON.stringify(dataUrl)}, { cache: 'no-store' }); return r.status`, expect: 401 },
  { name: 'five wrong guesses lock the form and count down', js: `${WAIT} const i = document.getElementById('secret'); for (let n = 0; n < 5; n++) { i.value = 'nope' + n; document.getElementById('form').requestSubmit(); await wait(700); } return [i.disabled, document.getElementById('msg').textContent.startsWith('Too many wrong tries. You can try again in ')]`, expect: [true, true], shot: shot('5-locked') },
  { name: 'while locked even the right ' + what + ' is refused', js: `const r = await fetch(${JSON.stringify(dataUrl.replace('/data', '/session'))}, { cache: 'no-store', headers: { Authorization: 'Basic ' + btoa('shop:' + ${JSON.stringify(secret)}) } }); return r.status`, expect: 429 },
];
