// Tests for the shopkeeper dashboard page (dukaan_dost/web/dashboard.html) that need no browser.
//   node --test tests/web/
import { test } from "node:test";
import assert from "node:assert/strict";
import { composedPage } from "./composed.mjs";

const html = composedPage("dashboard");
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];

// The pure helpers sit between two markers so they can be tested without a DOM.
const helperSource = script.slice(script.indexOf("/* ---- helpers"), script.indexOf("/* ---- end helpers ---- */"));
const { rupees, itemsSummary, relTime, limitUsed, statusLabel, paymentLabel, fmtDate, greeting, change, shortRupees, barPercent, attention, callStatus, trendHasData, nextTheme, themeLabel, isPlainKey, menuOpen } = new Function(
  `${helperSource}; return { rupees, itemsSummary, relTime, limitUsed, statusLabel, paymentLabel, fmtDate, greeting, change, shortRupees, barPercent, attention, callStatus, trendHasData, nextTheme, themeLabel, isPlainKey, menuOpen };`)();

test("the page script is valid JavaScript", () => {
  new Function(script);
});

test("the page never builds HTML from data", () => {
  for (const banned of ["innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval(", "new Function"]) {
    assert.ok(!script.includes(banned), `uses ${banned}`);
  }
});

test("the page loads nothing from outside its own server", () => {
  assert.doesNotMatch(html, /(?:src|href)=["']https?:/i);
  assert.doesNotMatch(script, /https?:\/\//i);
});

test("the page asks the server for its data at the address the server serves it", () => {
  assert.match(script, /location\.origin \+ location\.pathname/);
  assert.match(script, /'\/data'/);
});

test("rupees use Indian digit grouping", () => {
  assert.equal(rupees(285), "₹285");
  assert.equal(rupees(100000), "₹1,00,000");
  assert.equal(rupees(1000000), "₹10,00,000");
  assert.equal(rupees(4500000), "₹45,00,000");
  assert.equal(rupees(null), "₹0");
  assert.equal(rupees("12345"), "₹12,345");
});

test("an order's items are summarised, with a count of the rest", () => {
  const items = [{ name: "Rice", qty: 2, unit: "kg" }, { name: "Oil", qty: 1, unit: "litre" },
                 { name: "Salt", qty: 1, unit: "kg" }, { name: "Tea", qty: 1, unit: "pack" }];
  assert.equal(itemsSummary(items.slice(0, 2)), "2 kg Rice, 1 litre Oil");
  assert.equal(itemsSummary(items), "2 kg Rice, 1 litre Oil, 1 kg Salt +1 more");
  assert.equal(itemsSummary([]), "");
  assert.equal(itemsSummary([{ name: "Soap" }]), "Soap");
});

test("relative times read naturally", () => {
  const now = new Date("2026-11-02T15:00:00");
  assert.equal(relTime("2026-11-02T14:59:40", now), "just now");
  assert.equal(relTime("2026-11-02T14:56:00", now), "4 min ago");
  assert.match(relTime("2026-11-02T12:00:00", now), /^3 h ago, /);
  assert.match(relTime("2026-11-01T18:20:00", now), /^yesterday /);
  assert.match(relTime("2026-10-20T09:00:00", now), /^20 Oct /);
  assert.equal(relTime("not a date", now), "");
});

test("dates are shown without a time-zone shift", () => {
  assert.equal(fmtDate("2026-10-28"), "28 Oct");
  assert.equal(fmtDate("2026-01-05"), "5 Jan");
  assert.equal(fmtDate("2026-12-31"), "31 Dec");
  assert.equal(fmtDate(null), "");
  assert.equal(fmtDate("28/10/2026"), "");
});

test("the credit limit bar is clamped and survives a zero limit", () => {
  assert.equal(limitUsed(500, 1000), 0.5);
  assert.equal(limitUsed(2500, 1000), 1);
  assert.equal(limitUsed(-5, 1000), 0);
  assert.equal(limitUsed(100, 0), 0);
});

test("status and payment labels", () => {
  assert.equal(statusLabel("credit_pending"), "Credit pending");
  assert.equal(statusLabel("incomplete"), "Incomplete");
  assert.equal(statusLabel(undefined), "Confirmed");
  assert.equal(paymentLabel("udhaar"), "On credit");
  assert.equal(paymentLabel("upi"), "UPI");
});

test("the greeting follows the hour", () => {
  assert.equal(greeting(6), "Good morning!");
  assert.equal(greeting(12), "Good afternoon!");
  assert.equal(greeting(16), "Good afternoon!");
  assert.equal(greeting(17), "Good evening!");
});

test("today against yesterday never divides by zero", () => {
  assert.deepEqual(change(24, 20), { text: "▲ +20% vs yesterday", dir: "up" });
  assert.deepEqual(change(8, 10), { text: "▼ -20% vs yesterday", dir: "down" });
  assert.deepEqual(change(10, 10), { text: "same as yesterday", dir: "" });
  assert.deepEqual(change(5, 0), { text: "nothing yesterday", dir: "" });
  assert.deepEqual(change(0, 0), { text: "no change", dir: "" });
  assert.deepEqual(change(undefined, null), { text: "no change", dir: "" });
});

test("bar labels and heights", () => {
  assert.equal(shortRupees(950), "₹950");
  assert.equal(shortRupees(1000), "₹1k");
  assert.equal(shortRupees(4820), "₹4.8k");
  assert.equal(barPercent(50, 100), 50);
  assert.equal(barPercent(0, 100), 2);               // a zero day still shows a sliver
  assert.equal(barPercent(5, 0), 2);                 // and an all-zero week does not divide by zero
});

test("what needs the shopkeeper: problem orders and customers near their limit", () => {
  const orders = [{ status: "confirmed", total: 100 }, { status: "incomplete", customer: "Suresh", total: 300 },
                  { status: "credit_pending", customer: "Anita", total: 260 }, { status: "credit_pending", total: 50 }];
  const ledger = [{ name: "Anita", balance: 1900, credit_limit: 2000 }, { name: "Ramesh", balance: 685, credit_limit: 2000 },
                  { name: "Nobody", balance: 0, credit_limit: 0 }];
  const out = attention(orders, ledger);
  assert.deepEqual(out.map(a => a.title), ["Suresh: incomplete order", "Anita: credit pending", "A caller: credit pending", "Anita: credit near the limit"]);
  assert.equal(out[3].tag, "₹1,900 / ₹2,000");
  assert.deepEqual(attention([], []), []);
  assert.deepEqual(attention(undefined, undefined), []);
});

test("the call line", () => {
  assert.equal(callStatus([]), "No call right now");
  assert.equal(callStatus([{ seconds: 75 }]), "A customer is on a call (1:15)");
});

// ---- rules both pages follow (docs: MD/frontend.md, "Design system") ----
const tokenFree = (src) => src.replace(/:root[^{]*\{[^}]*\}/g, "");           // drop the token rules themselves

test("no colour is written outside the tokens", () => {
  const style = html.match(/<style>([\s\S]*?)<\/style>/)[1];
  const left = tokenFree(style).match(/#[0-9a-fA-F]{3,8}|rgba?\(|hsla?\(/g);
  assert.equal(left, null, `literal colours outside the token rules: ${left}`);
});

test("the theme is applied before the page paints, under the same key on both pages", () => {
  const init = html.match(/<script id="theme-init">([\s\S]*?)<\/script>/);
  assert.ok(init, "missing the head script that sets the saved theme");
  assert.ok(html.indexOf('id="theme-init"') < html.indexOf("<style>"), "the theme script must run before the CSS");
  assert.match(init[1], /dd:theme/);
  assert.match(script, /localStorage\.setItem\('dd:theme'/);
  new Function(init[1]);
});

test("dark tokens apply by device unless Light is chosen, and when Dark is chosen", () => {
  assert.match(html, /prefers-color-scheme:dark\)\{:root:not\(\[data-theme="light"\]\)\{/);
  assert.match(html, /:root\[data-theme="dark"\]\{/);
});

test("touch targets are 44px on a coarse pointer", () => {
  assert.match(html, /@media \(pointer:coarse\)\{[^}]*min-height:44px/);
});

test("theme and shortcut helpers", () => {
  assert.equal(nextTheme("auto"), "light");
  assert.equal(nextTheme("light"), "dark");
  assert.equal(nextTheme("dark"), "auto");
  assert.equal(nextTheme("nonsense"), "auto");
  assert.equal(themeLabel("dark"), "Dark");
  assert.equal(themeLabel(undefined), "Auto");
  const key = (over) => ({ target: { tagName: "BODY" }, ...over });
  assert.equal(isPlainKey(key({})), true);
  assert.equal(isPlainKey(key({ ctrlKey: true })), false);       // browser shortcuts still work
  assert.equal(isPlainKey(key({ metaKey: true })), false);
  assert.equal(isPlainKey(key({ altKey: true })), false);
  assert.equal(isPlainKey(key({ repeat: true })), false);        // holding a key must not flap the theme
  assert.equal(isPlainKey(key({ defaultPrevented: true })), false);
  assert.equal(isPlainKey(key({ target: { tagName: "INPUT", type: "text" } })), false);   // never while typing
  assert.equal(isPlainKey(key({ target: { tagName: "TEXTAREA" } })), false);
  assert.equal(isPlainKey(key({ target: { tagName: "INPUT", type: "checkbox" } })), true);
});

test("the comparison says which yesterday it is", () => {
  assert.deepEqual(change(12, 10, "vs this time yesterday"), { text: "▲ +20% vs this time yesterday", dir: "up" });
  assert.equal(change(12, 10).text, "▲ +20% vs yesterday");               // the default wording is unchanged
});

test("a week with no sales is an empty state, not seven zero bars", () => {
  assert.equal(trendHasData([]), false);
  assert.equal(trendHasData(undefined), false);
  assert.equal(trendHasData([{ sales: 0 }, { sales: 0 }]), false);
  assert.equal(trendHasData([{ sales: 0 }, { sales: 50 }]), true);
});

test("loading is not drawn as emptiness, and a section change moves focus", () => {
  assert.match(script, /function renderLoading\(/);
  assert.match(script, /renderLoading\(\);\s*showView\(\);/);          // skeletons are on screen before the first answer
  assert.match(script, /hashchange', \(\) => showView\(true\)/);
  assert.match(html, /<h2 id="hello" tabindex="-1">/);
});

test("the menu is open unless it was hidden on purpose", () => {
  assert.equal(menuOpen(null), true);
  assert.equal(menuOpen(undefined), true);
  assert.equal(menuOpen("open"), true);
  assert.equal(menuOpen("closed"), false);
  assert.equal(menuOpen("garbage"), true);               // a bad stored value never traps the user without a menu
});

test("a hidden menu is applied before the page paints, under the same key the page saves", () => {
  const init = html.match(/<script id="menu-init">([\s\S]*?)<\/script>/);
  assert.ok(init, "missing the head script that restores a hidden menu");
  assert.ok(html.indexOf('id="menu-init"') < html.indexOf("<style>"), "it must run before the CSS");
  assert.match(init[1], /dd:menu/);
  assert.match(script, /localStorage\.setItem\('dd:menu'/);
  new Function(init[1]);
});

test("the menu can be hidden and brought back, by button and by key, and focus is handed on", () => {
  assert.match(html, /id="menuhide"[^>]*aria-expanded="true"[^>]*aria-controls="sidemenu"/);
  assert.match(html, /id="menushow"[^>]*aria-expanded="true"[^>]*aria-controls="sidemenu"/);
  assert.match(html, /<aside id="sidemenu">/);
  assert.match(script, /\(open \? \$\('menuhide'\) : \$\('menushow'\)\)\.focus\(\)/);
  assert.match(script, /key\.toLowerCase\(\) === 'b'/);
  assert.match(html, /html\[data-menu=closed\] aside\{transform:translateX\(-110%\);visibility:hidden\}/);   // slides out to the left, and leaves the tab order
});

test("the menu has the curved right end", () => {
  assert.match(html, /aside\{[^}]*border-radius:0 30px 30px 0/);
});

test("the menu has a Call page link, and it goes to this shop's own call page", () => {
  assert.match(html, /<a class="nav" id="callpage" href="\/"[^>]*>[\s\S]*?Call page<\/a>/);
  assert.match(script, /\$\('callpage'\)\.setAttribute\('href', callPageUrl\(location\.pathname\)\)/);
  const { callPageUrl } = new Function(`${helperSource}; return { callPageUrl };`)();
  assert.equal(callPageUrl("/s/dukaan_dost/dashboard"), "/s/dukaan_dost/");
  assert.equal(callPageUrl("/s/alpha/dashboard/"), "/s/alpha/");
  assert.equal(callPageUrl("/s/a-b_1/dashboard"), "/s/a-b_1/");
  assert.equal(callPageUrl("/dashboard"), "/");                         // not a shop's address: the plain call page
  assert.equal(callPageUrl("/s/x/dashboard/data"), "/");
  assert.equal(callPageUrl(undefined), "/");
});

test("the Calls view lists every ended call, and the menu leads to it with today's count", () => {
  assert.match(html, /<a class="nav" href="#calls" data-view="calls">[\s\S]*?Calls<span class="n" id="navcalls" hidden><\/span><\/a>/);
  assert.match(html, /<div data-page="calls" hidden>[\s\S]*?<h2 tabindex="-1">Calls<\/h2>[\s\S]*?id="callslist"/);
  assert.match(html, /no words, no recording, no phone numbers/);       // says what is not kept
  assert.match(script, /renderCalls\(d\.calls \|\| \[\], d\.summary\)/);   // an older server without calls still draws
  assert.match(script, /\.\.\.\(d\.calls \|\| \[\]\)\]\.some\(r => r\.synthetic\)/);
  assert.match(script, /'loans', 'callslist'\]/);                       // a skeleton while loading, not "no calls"
});

test("a call's length, language and what came of it read in plain words", () => {
  const { callLength, languageName, callOutcome, callMeta, callNotes, callsLine } = new Function(
    `${helperSource}; return { callLength, languageName, callOutcome, callMeta, callNotes, callsLine };`)();
  assert.equal(callLength(192), "3:12");
  assert.equal(callLength(5), "0:05");
  assert.equal(callLength(-3), "0:00");
  assert.equal(callLength(null), "0:00");
  assert.equal(languageName("te-IN"), "Telugu");
  assert.equal(languageName("hi-en"), "Hinglish");
  assert.equal(languageName(null), "");
  assert.equal(languageName("xx"), "");
  assert.deepEqual(callOutcome({ outcome: "ordered", status: "confirmed" }), { text: "Ordered", cls: "confirmed" });
  assert.deepEqual(callOutcome({ outcome: "ordered", status: "credit_pending" }), { text: "Ordered, credit pending", cls: "credit_pending" });
  assert.deepEqual(callOutcome({ outcome: "ordered", status: "incomplete" }), { text: "Order incomplete", cls: "incomplete" });
  assert.deepEqual(callOutcome({ outcome: "loan" }), { text: "Loan guidance", cls: "loan" });
  assert.deepEqual(callOutcome({ outcome: "nothing" }), { text: "No order", cls: "none" });
  assert.deepEqual(callOutcome({}), { text: "No order", cls: "none" });
  assert.equal(callMeta({ language: "hi-IN", seconds: 192, turns: 7 }), "Hindi · 3:12 · spoke 7 times");
  assert.equal(callMeta({ language: "en-IN", seconds: 40, turns: 1 }), "English · 0:40 · spoke once");
  assert.equal(callMeta({ language: null, seconds: 18, turns: 0 }), "0:18 · nothing understood");
  assert.deepEqual(callNotes({ barge_ins: 0, no_speech: 0, model_failures: 0 }), []);
  assert.deepEqual(callNotes({}), []);
  assert.deepEqual(callNotes({ model_failures: 2, no_speech: 1, barge_ins: 3 }), [
    { kind: "warn", text: "The agent could not answer twice" },
    { kind: "", text: "Speech not caught once" },
    { kind: "", text: "Caller cut in 3 times" },
  ]);
  assert.equal(callsLine({ calls_today: 1, calls_total: 1 }), "1 call today, 1 in all.");
  assert.equal(callsLine({ calls_today: 0, calls_total: 12 }), "No calls yet today, 12 in all.");
  assert.equal(callsLine({}), "No calls yet today.");
  assert.equal(callsLine(undefined), "No calls yet today.");
});
