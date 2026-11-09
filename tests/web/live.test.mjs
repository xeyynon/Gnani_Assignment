// Tests for the full-screen Live call page (dukaan_dost/web/live.html) that need no browser.
//   node --test tests/web/
import { test } from "node:test";
import assert from "node:assert/strict";
import { composedPage } from "./composed.mjs";

const html = composedPage("live");
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];

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

test("the page asks the dashboard's own data feed, not a feed of its own", () => {
  assert.match(script, /\/dashboard\/data/);
  assert.match(script, /poll\(/);
});

test("the page has every element the shared Live and poll code looks for", () => {
  for (const id of ["title", "dot", "updated", "notices", "liveline", "navlive", "liveempty", "liveon", "livelog", "liveorder", "liveloanbox", "liveloan", "themebtn", "todash"]) {
    assert.match(html, new RegExp(`id="${id}"`), `missing #${id}`);
  }
});

test("the page says plainly that nothing said on it is saved", () => {
  assert.match(html, /Nothing said here is saved/);
});

test("the page has no sign-in bypass: no demo switch, no key in the address", () => {
  assert.doesNotMatch(html, /DEMO_LIVE|bypass|\?pin=|\?key=/i);
});

test("the empty state is for watching, with no 'try a call' link", () => {
  const last = script.slice(script.lastIndexOf("EMPTY.live =")).split("\n")[0];       // the page's own line, after the dashboard's helper one
  assert.match(last, /title: 'Waiting for a call'/);
  assert.doesNotMatch(last, /action/);
  assert.ok(script.lastIndexOf("EMPTY.live =") < script.indexOf("emptyCard(EMPTY.live)"), "the override must come before the page draws the empty card");
});

// ---- several calls at once -------------------------------------------------------------------------------------
const helperSource = script.slice(script.indexOf("/* ---- helpers"), script.indexOf("/* ---- end helpers ---- */"));
const { liveTabLabels, liveSelection } = new Function(`${helperSource}; return { liveTabLabels, liveSelection };`)();

test("each call gets a tab that says which call, how it came in and how long it has lasted", () => {
  assert.deepEqual(liveTabLabels([{ channel: "phone", seconds: 65 }, { channel: "browser", seconds: 5 }, {}]),
    ["Call 1: Phone, 1:05", "Call 2: Browser, 0:05", "Call 3"]);
});

test("no calls, or nonsense instead of a list, gives no tabs", () => {
  assert.deepEqual(liveTabLabels([]), []);
  assert.deepEqual(liveTabLabels(null), []);
  assert.deepEqual(liveTabLabels(undefined), []);
});

test("the call being watched is kept while it is on, and falls back to the first when it is gone", () => {
  assert.equal(liveSelection(1, 3), 1);
  assert.equal(liveSelection(2, 2), 0);          // that call ended
  assert.equal(liveSelection(-1, 2), 0);
  assert.equal(liveSelection(NaN, 2), 0);
  assert.equal(liveSelection(undefined, 0), 0);
});

test("the page has a tab bar for several calls, hidden until there are two", () => {
  assert.match(html, /id="livetabs"[^>]*hidden/);
  assert.match(html, /id="livecount"/);
  assert.match(script, /drawLive\(/);
});
