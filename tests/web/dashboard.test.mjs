// Tests for the shopkeeper dashboard page (dukaan_dost/web/dashboard.html) that need no browser.
//   node --test tests/web/
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const html = readFileSync(new URL("../../dukaan_dost/web/dashboard.html", import.meta.url), "utf8");
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];

// The pure helpers sit between two markers so they can be tested without a DOM.
const helperSource = script.slice(script.indexOf("/* ---- helpers"), script.indexOf("/* ---- end helpers ---- */"));
const { rupees, itemsSummary, relTime, limitUsed, statusLabel, paymentLabel, fmtDate } = new Function(
  `${helperSource}; return { rupees, itemsSummary, relTime, limitUsed, statusLabel, paymentLabel, fmtDate };`)();

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
