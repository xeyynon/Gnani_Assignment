// Tests for the sign-in page (dukaan_dost/web/login.html) that need no browser. The server side is tests/test_login.py;
// a real browser walks the whole thing with scripts/ui_check/flows/login.mjs.
//   node --test tests/web/
import { test } from "node:test";
import assert from "node:assert/strict";
import { composedPage } from "./composed.mjs";

const html = composedPage("login");
const script = html.match(/<script>([\s\S]*?)<\/script>/g).map(s => s.replace(/<\/?script>/g, "")).join("\n");
const mainScript = html.match(/<script>(?!window)([\s\S]*?)<\/script>/)[1];
const helperSource = mainScript.slice(mainScript.indexOf("/* ---- helpers"), mainScript.indexOf("/* ---- end helpers ---- */"));
const { credentialHeader, clock, triesText, lockText, whatWord, loginOutcome, loginWords, nextTheme, themeLabel } = new Function(
  `${helperSource}; return { credentialHeader, clock, triesText, lockText, whatWord, loginOutcome, loginWords, nextTheme, themeLabel };`)();

test("the page script is valid JavaScript", () => {
  new Function(mainScript);
});

test("the page never builds HTML from data", () => {
  for (const banned of ["innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval(", "new Function"]) {
    assert.ok(!script.includes(banned), `uses ${banned}`);
  }
});

test("the page loads nothing from outside its own server, and has no inline event handlers", () => {
  assert.doesNotMatch(html, /(?:src|href)=["']https?:/i);
  assert.doesNotMatch(script, /https?:\/\//i);
  assert.doesNotMatch(html, /\son[a-z]+=["']/i);
});

test("the placeholders the server fills are all there, and only those", () => {
  const found = [...new Set([...html.matchAll(/\{\{(\w+)\}\}/g)].map(m => m[1]))].sort();
  assert.deepEqual(found, ["BACK_URL", "KIND", "NOPIN", "SESSION_URL", "THEME", "TITLE"]);
});

test("the PIN is sent in a header and never put in an address or stored", () => {
  const loginPart = mainScript.slice(mainScript.indexOf("/* ---- the sign-in page: one GET"));      // not theme.js, which keeps the theme choice
  assert.match(loginPart, /headers: \{ Authorization: credentialHeader/);
  assert.doesNotMatch(loginPart, /localStorage|sessionStorage|document\.cookie/);
  assert.doesNotMatch(loginPart, /\?pin=|\?password=|dataset\.session \+ .*secret/);
});

test("the form works with a password manager and a phone keypad", () => {
  assert.match(html, /autocomplete="current-password"/);
  assert.match(html, /autocomplete="username"/);
  assert.match(html, /inputmode="numeric"/);
  assert.match(html, /enterkeyhint="go"/);
  assert.match(html, /<label for="secret" id="secret-label">/);
});

test("a message is announced, the field says it is wrong, and the show button says what it does", () => {
  assert.match(html, /id="msg" role="alert"/);
  assert.match(mainScript, /setAttribute\('aria-invalid', 'true'\)/);
  assert.match(html, /id="peek" aria-pressed="false" aria-label="Show PIN"/);
});

test("the page has a main landmark, one h1 and a title", () => {
  assert.equal((html.match(/<main[ >]/g) || []).length, 1);
  assert.equal((html.match(/<h1[ >]/g) || []).length, 1);
  assert.match(html, /<title>Sign in: \{\{TITLE\}\}<\/title>/);
});

test("the credential header is the same Basic header a script sends, UTF-8 safe", () => {
  assert.equal(credentialHeader("shop", "1234"), "Basic " + Buffer.from("shop:1234").toString("base64"));
  assert.equal(credentialHeader("shop", "पिन९९ü"), "Basic " + Buffer.from("shop:पिन९९ü", "utf8").toString("base64"));
  assert.equal(credentialHeader("admin", "a:b"), "Basic " + Buffer.from("admin:a:b").toString("base64"));   // a colon in the password is kept
});

test("the lock countdown reads as minutes and seconds", () => {
  assert.equal(clock(42), "0:42");
  assert.equal(clock(60), "1:00");
  assert.equal(clock(125), "2:05");
  assert.equal(clock(0), "0:00");
  assert.equal(clock(-5), "0:00");
  assert.equal(clock(41.2), "0:42");                 // a part second counts as a whole one, so it never shows 0:00 while still locked
  assert.equal(clock("x"), "0:00");
  assert.equal(lockText(42), "Too many wrong tries. You can try again in 0:42.");
});

test("tries left read naturally", () => {
  assert.equal(triesText(1), "1 try left");
  assert.equal(triesText(4), "4 tries left");
});

test("the server's answer becomes what the page says, for a PIN and for the admin password", () => {
  assert.deepEqual(loginOutcome(200, { ok: true }, "shop"), { kind: "ok", text: "Signed in. Opening the page..." });
  assert.deepEqual(loginOutcome(401, { ok: false, wrong: true, remaining: 4 }, "shop"), { kind: "wrong", text: "That PIN is not right. 4 tries left." });
  assert.deepEqual(loginOutcome(401, { ok: false, wrong: true, remaining: 1 }, "admin"), { kind: "wrong", text: "That password is not right. 1 try left." });
  assert.equal(loginOutcome(401, { wrong: true }, "shop").text, "That PIN is not right.");
  assert.deepEqual(loginOutcome(429, { locked: true, retry_after: 42 }, "shop"), { kind: "locked", wait: 42, text: "Too many wrong tries. You can try again in 0:42." });
  assert.equal(loginOutcome(429, {}, "shop").wait, 60);
  assert.deepEqual(loginOutcome(400, { empty: true }, "shop"), { kind: "empty", text: "Enter your PIN." });
  assert.equal(loginOutcome(400, {}, "admin").text, "Enter your password.");
  assert.equal(loginOutcome(0, {}, "shop").kind, "error");
  assert.match(loginOutcome(0, {}, "shop").text, /Could not reach the server/);
  assert.match(loginOutcome(500, {}, "shop").text, /Something went wrong \(500\)/);
});

test("odd answers never crash the page", () => {
  for (const data of [null, undefined, "text", 5, [], { remaining: "many", wrong: true }]) {
    const o = loginOutcome(401, data, "shop");
    assert.ok(typeof o.text === "string" && o.text.length > 0);
  }
  assert.equal(loginOutcome(401, { wrong: true, remaining: 0 }, "shop").text, "That PIN is not right.");
});

test("the fixed words differ for a shop and the admin, and the shop page links to the call page and the admin", () => {
  assert.equal(whatWord("admin"), "password");
  assert.equal(whatWord("shop"), "PIN");
  const shop = loginWords("shop", false), admin = loginWords("admin", false);
  assert.equal(shop.back, true);
  assert.equal(shop.admin, true);
  assert.equal(admin.back, false);
  assert.equal(admin.admin, false);
  assert.match(shop.help, /Forgot your PIN/);
  assert.equal(loginWords("shop", true).help, "");
});

test("the theme helpers the page shares behave as on the other pages", () => {
  assert.equal(nextTheme("auto"), "light");
  assert.equal(themeLabel("dark"), "Dark");
});

test("typing a t in the PIN box does not switch the theme", () => {
  const { isPlainKey } = new Function(`${helperSource}; return { isPlainKey };`)();
  assert.equal(isPlainKey({ key: "t", target: { tagName: "INPUT", type: "password" } }), false);
  assert.equal(isPlainKey({ key: "t", target: { tagName: "INPUT", type: "text" } }), false);
});

test("the admin page and the shop dashboard have a sign-out button that calls the server", () => {
  for (const name of ["dashboard", "admin"]) {
    const page = composedPage(name);
    assert.match(page, /id="signout"/);
    assert.match(page, /'\/signout'/);
    assert.match(page, /credentials: 'same-origin'/);
  }
});
