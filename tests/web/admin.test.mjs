// Tests for the admin page (dukaan_dost/web/admin.html, composed from components) that need no browser.
//   node --test tests/web/
import { test } from "node:test";
import assert from "node:assert/strict";
import { composedPage } from "./composed.mjs";

const html = composedPage("admin");
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];

const helperSource = script.slice(script.indexOf("/* ---- helpers"), script.indexOf("/* ---- end helpers ---- */"));
const { stateView, severityView, plural, liveText, shopSub, problemSub, validShopId, slugify, shopIdProblem, pinProblem, parseAliases,
  newItem, newItemProblem, stockChanges, changeSummary, STOCK_UNITS, rupees, relTime } = new Function(
  `${helperSource}; return { stateView, severityView, plural, liveText, shopSub, problemSub, validShopId, slugify, shopIdProblem, pinProblem, parseAliases,
  newItem, newItemProblem, stockChanges, changeSummary, STOCK_UNITS, rupees, relTime };`)();

test("the page script is valid JavaScript", () => {
  new Function(script);
});

test("the page never builds HTML from data (shop names and problem text are free text)", () => {
  for (const banned of ["innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval(", "new Function"]) {
    assert.ok(!script.includes(banned), `uses ${banned}`);
  }
});

test("the page loads nothing from outside its own server", () => {
  assert.doesNotMatch(html, /(?:src|href)=["']https?:/i);
  assert.doesNotMatch(script, /https?:\/\//i);
});

test("the page asks the admin data route, and nothing else", () => {
  assert.match(script, /location\.origin \+ '\/admin\/data'/);
});

test("no colour is written outside the tokens", () => {
  const style = html.match(/<style>([\s\S]*?)<\/style>/)[1];
  const left = style.replace(/:root[^{]*\{[^}]*\}/g, "").match(/#[0-9a-fA-F]{3,8}|rgba?\(|hsla?\(/g);
  assert.equal(left, null, `literal colours outside the token rules: ${left}`);
});

test("the theme and menu are restored before the page paints", () => {
  assert.ok(html.indexOf('id="theme-init"') < html.indexOf("<style>"));
  assert.ok(html.indexOf('id="menu-init"') < html.indexOf("<style>"));
});

test("a shop's state is always shown with a word, and an unknown state is never shown as ready", () => {
  assert.deepEqual(stateView("ready"), ["confirmed", "Ready"]);
  assert.deepEqual(stateView("attention"), ["credit_pending", "Needs attention"]);
  assert.deepEqual(stateView("broken"), ["incomplete", "Broken"]);
  assert.equal(stateView("???")[1], "Needs attention");
  assert.equal(stateView(undefined)[1], "Needs attention");
});

test("problem severity", () => {
  assert.deepEqual(severityView("error"), ["incomplete", "Error"]);
  assert.deepEqual(severityView("warning"), ["credit_pending", "Warning"]);
  assert.equal(severityView("anything else")[1], "Warning");
});

test("plural", () => {
  assert.equal(plural(1, "problem", "problems"), "1 problem");
  assert.equal(plural(0, "problem", "problems"), "0 problems");
  assert.equal(plural(12, "problem", "problems"), "12 problems");
});

test("the call line", () => {
  assert.equal(liveText([]), "No call right now");
  assert.equal(liveText(undefined), "No call right now");
  assert.equal(liveText([75]), "A customer is on a call (1:15)");
  assert.equal(liveText([5, 80]), "2 calls (0:05)");
});

test("the line under the Shops tile says what is not fine, and nothing it cannot know", () => {
  assert.equal(shopSub({ shops: 0 }), "none yet");
  assert.equal(shopSub({ shops: 3, shops_ready: 3, shops_attention: 0, shops_broken: 0 }), "3 ready");
  assert.equal(shopSub({ shops: 3, shops_ready: 1, shops_attention: 1, shops_broken: 1 }), "1 ready, 1 need attention, 1 broken");
});

test("the shared formatters work here too", () => {
  assert.equal(rupees(125000), "₹1,25,000");
  assert.equal(relTime("not a date", new Date()), "");
});

test("the menu names the sections, and nothing in it is a placeholder", () => {
  for (const v of ["overview", "problems", "add"]) assert.match(html, new RegExp(`class="nav" href="#${v}" data-view="${v}"`));
  assert.doesNotMatch(html, /aria-disabled="true"/);
  assert.doesNotMatch(html, /class="soon"/);
  for (const v of ["problems", "add", "edit"]) assert.match(html, new RegExp(`data-page="${v}" hidden`));
});

test("the overview carries no money: that is the shopkeeper's business", () => {
  assert.doesNotMatch(html, /Sales today|Owed on credit|udhaar_outstanding|sales_today/);
});

test("a shop with no orders says so instead of showing a date", () => {
  assert.match(script, /s\.last_order \? relTime\(s\.last_order\) : 'no orders yet'/);
});

test("the page keeps its commands off the page address and its token off the page", () => {
  assert.match(script, /fetch\('\/admin\/token'/);
  assert.match(script, /\/admin\/ws/);
  assert.match(script, /cmd: 'hello', token/);
  assert.doesNotMatch(html, /localStorage\.setItem\([^)]*token/i);       // the token is never stored
});

test("every command the page sends is one the server knows", () => {
  const sent = [...script.matchAll(/adminCall\('([a-z_]+)'/g)].map(m => m[1]);
  assert.deepEqual([...new Set(sent)].sort(), ["create_shop", "dismiss", "get_shop", "restore", "save_prompt", "save_stock", "set_pin"]);
});

test("every field has a label the screen reader can use", () => {
  const ids = [...html.matchAll(/<(?:input|select|textarea)[^>]*\bid="([^"]+)"/g)].map(m => m[1]);
  assert.ok(ids.length >= 12);
  for (const id of ids) assert.match(html, new RegExp(`<label for="${id}"`), `no label for #${id}`);
});

test("every button written into the page says what it does", () => {
  for (const m of html.matchAll(/<button\b([^>]*)>([\s\S]*?)<\/button>/g)) {
    const named = /aria-label="[^"]+"/.test(m[1]) || m[2].replace(/<[^>]*>/g, "").trim().length > 0;
    assert.ok(named, `a button with no name: ${m[0].slice(0, 80)}`);
  }
});

test("a link name follows the server's rule", () => {
  for (const ok of ["ab", "sri_lakshmi", "shop-2", "9shop", "a".repeat(40)]) assert.equal(validShopId(ok), true, ok);
  for (const bad of ["", "a", "A", "Shop", "-shop", "_shop", "a b", "a/b", "../x", "a".repeat(41), null, undefined, 5]) assert.equal(validShopId(bad), false, String(bad));
  assert.equal(shopIdProblem(""), "Give the shop a link name.");
  assert.equal(shopIdProblem("Bad Name") !== "", true);
  assert.equal(shopIdProblem("good_name"), "");
});

test("a shop's name becomes a usable link name", () => {
  assert.equal(slugify("Sri Lakshmi Kirana Store"), "sri_lakshmi_kirana_store");
  assert.equal(slugify("  Raju's  Corner!! "), "raju_s_corner");
  assert.equal(slugify("శ్రీ దుకాణం"), "");                           // nothing usable: the typist is asked, no nonsense is invented
  assert.equal(slugify("x".repeat(60)).length, 40);
  assert.equal(slugify(null), "");
  for (const t of ["Sri Lakshmi", "Shop 2", "  --Odd--  "]) assert.equal(validShopId(slugify(t)), true, t);
});

test("a PIN may be left empty but not be short", () => {
  assert.equal(pinProblem(""), "");
  assert.equal(pinProblem(undefined), "");
  assert.equal(pinProblem("123").length > 0, true);
  assert.equal(pinProblem("1234"), "");
});

test("aliases are trimmed, lower cased and not repeated", () => {
  assert.deepEqual(parseAliases("Rice, chawal , RICE,, "), ["rice", "chawal"]);
  assert.deepEqual(parseAliases(""), []);
  assert.deepEqual(parseAliases(null), []);
});

test("a new item is built the way stock.json wants it, and is checked before it is sent", () => {
  const form = { sku: " sugar-1kg ", en: " Sugar ", hi: "चीनी", te: "చక్కెర", unit: "kg", price: "44", aliases: "sugar, cheeni" };
  const item = newItem(form);
  assert.deepEqual(item, { sku: "SUGAR-1KG", category: "other", unit: "kg", price: 44, in_stock: true,
    name: { en: "Sugar", hi: "चीनी", te: "చక్కెర" }, pack: "per kg", aliases: ["sugar", "cheeni"] });
  assert.equal(newItemProblem(item), "");
  const probs = [
    [{ sku: "x" }, /item code/], [{ en: "" }, /English, Hindi and Telugu/], [{ te: " " }, /English, Hindi and Telugu/],
    [{ unit: "tonne" }, /unit/], [{ unit: "" }, /unit/], [{ price: "0" }, /price/], [{ price: "abc" }, /price/], [{ price: "-3" }, /price/],
    [{ aliases: " , " }, /way callers say/]];
  for (const [change, re] of probs) assert.match(newItemProblem(newItem({ ...form, ...change })), re, JSON.stringify(change));
});

test("the units offered are the ones the server accepts", () => {
  assert.deepEqual([...STOCK_UNITS].sort(), ["bag", "bar", "bottle", "kg", "litre", "loaf", "packet", "piece"]);
});

test("stock edits become only the changes, and a bad price stops the save", () => {
  const original = [{ sku: "A", price: 10, in_stock: true }, { sku: "B", price: 20, in_stock: true }, { sku: "C", price: 30, in_stock: false }];
  const same = original.map(o => ({ ...o, remove: false }));
  assert.deepEqual(stockChanges(original, same), { update: [], remove: [], bad: [] });
  const edited = [{ sku: "A", price: 12, in_stock: true, remove: false }, { sku: "B", price: 20, in_stock: false, remove: false }, { sku: "C", price: 30, in_stock: false, remove: true }];
  assert.deepEqual(stockChanges(original, edited), { update: [{ sku: "A", price: 12 }, { sku: "B", in_stock: false }], remove: ["C"], bad: [] });
  const bad = stockChanges(original, [{ sku: "A", price: NaN, in_stock: true, remove: false }, { sku: "B", price: 0, in_stock: true, remove: false }, { sku: "C", price: -1, in_stock: false, remove: false }]);
  assert.deepEqual(bad.bad, ["A", "B", "C"]);
  assert.deepEqual(stockChanges(original, [{ sku: "Z", price: 5, in_stock: true, remove: false }]), { update: [], remove: [], bad: [] });   // an unknown row is ignored
  assert.equal(changeSummary({ update: [1, 2], remove: [1] }), "2 items changed, 1 removed");
  assert.equal(changeSummary({ update: [1], remove: [] }), "1 item changed");
});

test("the To fix tile says what is wrong, and says nothing is wrong when nothing is", () => {
  assert.equal(problemSub({ errors: 0, warnings: 0 }), "nothing wrong");
  assert.equal(problemSub({ errors: 1, warnings: 3 }), "1 error, 3 warnings");
  assert.equal(problemSub({ errors: 0, warnings: 1 }), "1 warning");
});

test("an error has no 'mark solved' button; a warning does", () => {
  assert.match(script, /p\.severity === 'error' \? null : h\('button'/);
});

test("a shop is opened for editing only from a safe address", () => {
  assert.match(script, /\^\[a-z0-9\]\[a-z0-9_-\]\{1,39\}\$\/\.test\(v\.part\)/);
});
