// Tests for the shopkeeper dashboard page (dukaan_dost/web/dashboard.html) that need no browser.
//   node --test tests/web/
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const html = readFileSync(new URL("../../dukaan_dost/web/dashboard.html", import.meta.url), "utf8");
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];

// The pure helpers sit between two markers so they can be tested without a DOM.
const helperSource = script.slice(script.indexOf("/* ---- helpers"), script.indexOf("/* ---- end helpers ---- */"));
const { rupees, itemsSummary, relTime, limitUsed, statusLabel, paymentLabel, fmtDate, greeting, change, shortRupees, barPercent, attention, callStatus } = new Function(
  `${helperSource}; return { rupees, itemsSummary, relTime, limitUsed, statusLabel, paymentLabel, fmtDate, greeting, change, shortRupees, barPercent, attention, callStatus };`)();

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
