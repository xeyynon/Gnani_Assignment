// Tests for the browser call page (dukaan_dost/web/index.html) that need no browser.
//   node --test tests/web/
import { test } from "node:test";
import assert from "node:assert/strict";
import { composedPage } from "./composed.mjs";

const html = composedPage("index");
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];

// The resampler is plain JavaScript; pull it out the same way the page embeds it in the audio worklet.
const fnSource = script.slice(script.indexOf("function makeResampler"), script.indexOf("const workletSource"));
const makeResampler = new Function(`${fnSource}; return makeResampler;`)();

function tone(rate, hz, seconds, amplitude) {
  const out = new Float32Array(Math.floor(rate * seconds));
  for (let i = 0; i < out.length; i++) out[i] = amplitude * Math.sin((2 * Math.PI * hz * i) / rate);
  return out;
}
const rms = (samples) => Math.sqrt(samples.reduce((s, v) => s + v * v, 0) / samples.length);

test("the page script is valid JavaScript", () => {
  new Function(script);           // parses without running
});

test("the page connects to /ws under its own address, so a shop's link calls that shop", () => {
  assert.match(script, /base \+ 'ws'/);
  // Run the page's own expression for the base address, not a copy of it.
  const expr = script.match(/const base = (location\.pathname[^;]*);/)[1];
  const baseFor = (pathname) => new Function("location", `return ${expr};`)({ pathname });
  assert.equal(baseFor("/s/ram_kirana/") + "ws", "/s/ram_kirana/ws");
  assert.equal(baseFor("/s/ram_kirana") + "ws", "/s/ram_kirana/ws");
  assert.equal(baseFor("/") + "ws", "/ws");
  assert.equal(baseFor("/index.html") + "ws", "/ws");
});

test("the shop name is a placeholder the server fills in", () => {
  assert.match(html, /<title>\{\{SHOP\}\}/);
  assert.match(html, /<h1>\{\{SHOP\}\}<\/h1>/);
});

test("the controls the user needs exist", () => {
  for (const id of ["start", "hang", "status", "level", "speaking"]) {
    assert.match(html, new RegExp(`id="${id}"`), `missing #${id}`);
  }
});

test("the audio worklet carries its own copy of the resampler", () => {
  assert.match(script, /makeResampler\.toString\(\)/);
});

for (const inRate of [48000, 44100, 32000, 16000]) {
  test(`resamples a 440 Hz tone from ${inRate} Hz to 16 kHz without changing its length or level`, () => {
    const resample = makeResampler(inRate, 16000);
    const input = tone(inRate, 440, 1, 0.5);
    const out = [];
    for (let i = 0; i < input.length; i += 128) {            // 128 samples at a time, like an AudioWorklet
      out.push(...resample(input.subarray(i, Math.min(i + 128, input.length))));
    }
    assert.ok(Math.abs(out.length / 16000 - 1) < 0.01, `got ${out.length} samples`);
    const level = rms(out) / 32768;                          // a 0.5-amplitude sine has RMS 0.354
    assert.ok(Math.abs(level - 0.354) < 0.04, `level ${level.toFixed(3)}`);
  });
}

test("loud input is clipped, not wrapped around", () => {
  const out = makeResampler(16000, 16000)(new Float32Array([1.5, -1.5, 1, -1]));
  assert.deepEqual(Array.from(out), [32767, -32768, 32767, -32768]);
});

// ---- the call screen's own helpers, pulled out the way the dashboard test does ----
const helperSource = script.slice(script.indexOf("/* ---- helpers"), script.indexOf("/* ---- end helpers"));
const { langName, clock, rupees, barHeight, nextTheme, themeLabel, isPlainKey, loanView } = new Function(
  `${helperSource}; return { langName, clock, rupees, barHeight, nextTheme, themeLabel, isPlainKey, loanView };`)();

test("language names", () => {
  assert.equal(langName("hi-IN"), "Hindi");
  assert.equal(langName("te-in"), "Telugu");
  assert.equal(langName("en-IN"), "English");
  assert.equal(langName("hi-en"), "Hinglish");
  assert.equal(langName("en-GB"), "English");        // falls back to the language part
  assert.equal(langName("xx-YY"), "");
  assert.equal(langName(undefined), "");
});

test("call timer", () => {
  assert.equal(clock(0), "0:00");
  assert.equal(clock(134.9), "2:14");
  assert.equal(clock(-5), "0:00");
});

test("rupees use Indian digit grouping", () => {
  assert.equal(rupees(158), "₹158");
  assert.equal(rupees(125000), "₹1,25,000");
});

test("waveform bars stay inside their box and are quiet when the level is zero", () => {
  for (const level of [-1, 0, 0.5, 1, 7]) {
    for (let i = 0; i < 37; i++) {
      const hgt = barHeight(level, i, 37, 1234);
      assert.ok(hgt >= 4 && hgt <= 56, `bar ${i} at level ${level} is ${hgt}`);
    }
  }
  assert.equal(barHeight(0, 18, 37, 999), 4);
});

test("what the server sends is shown as text, never as HTML", () => {
  for (const banned of ["innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval(", "new Function"]) {
    assert.ok(!script.includes(banned), `${banned} must not appear in the page script`);
  }
});

test("the page handles every message the server can send", () => {
  for (const type of ["ready", "busy", "stop", "user", "agent", "order", "loan"]) {
    assert.match(script, new RegExp(`m\.type === '${type}'`), `no handler for ${type}`);
  }
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

test("a button that disappears hands keyboard focus on, and Mute shows its key", () => {
  assert.match(script, /focusIfLost\(\$\('hang'\)\)/);
  assert.match(script, /focusIfLost\(\$\('start'\)\)/);
  assert.match(html, /Mute \(M\)/);
});

// ---- the loan panel: a quote the agent sent, laid out as it came ----
const QUOTE = { type: "loan", heard_amount: 100000, kind: "margin_money", business: "kirana", place: "Nandyal",
  margin_money: 100000, project_cost: 1000000, covered: true, scheme: "Term Loan Scheme", annual_rate_pct: 8, loan_amount: 900000,
  own_contribution: 100000, monthly_instalment: 15438, repayment_months: 78, moratorium_months: 6, total_repayment: 1204164, total_interest: 304164, indicative: true };

test("a covered quote is laid out exactly as the calculator gave it", () => {
  const v = loanView(QUOTE);
  assert.equal(v.covered, true);
  assert.equal(v.where, "kirana, Nandyal");
  assert.deepEqual(v.rows, [["Project cost", "₹10,00,000"], ["Your margin money", "₹1,00,000"], ["Loan", "₹9,00,000"],
    ["Scheme", "Term Loan Scheme, 8% a year"], ["Total interest", "₹3,04,164"]]);
  assert.deepEqual(v.emi, { amount: "₹15,438", months: 78, after: "after a 6-month moratorium" });
  assert.equal(v.note, "");
});

test("the page shows the figures it was given and never works one out", () => {
  const odd = loanView({ ...QUOTE, monthly_instalment: 99999, loan_amount: 12345, project_cost: 777777 });
  assert.equal(odd.emi.amount, "₹99,999");                                       // not recomputed from the loan
  assert.equal(odd.rows.find(r => r[0] === "Loan")[1], "₹12,345");
  assert.equal(odd.rows[0][1], "₹7,77,777");
});

test("a capped loan says the caller puts in more than the margin", () => {
  const v = loanView({ ...QUOTE, margin_money: 450000, project_cost: 4500000, loan_amount: 4500000, own_contribution: 500000 });
  assert.equal(v.note, "The loan is capped, so you put in ₹5,00,000.");
  assert.equal(loanView({ ...QUOTE, own_contribution: 100000 }).note, "");
});

test("a project above the scheme limit says no scheme applies and shows no loan figures", () => {
  const v = loanView({ type: "loan", business: "", place: "", margin_money: 6000000, project_cost: 60000000, covered: false, scheme: null,
    annual_rate_pct: null, loan_amount: null, own_contribution: null, monthly_instalment: null, repayment_months: null, moratorium_months: null,
    total_interest: null, indicative: true });
  assert.equal(v.covered, false);
  assert.equal(v.emi, null);
  assert.deepEqual(v.rows, [["Project cost", "₹6,00,00,000"], ["Your margin money", "₹60,00,000"]]);
  assert.match(v.note, /no scheme applies/);
  assert.equal(v.where, "");
});

test("no moratorium is said plainly, and a missing instalment shows no instalment box", () => {
  assert.equal(loanView({ ...QUOTE, moratorium_months: 0 }).emi.after, "no moratorium");
  assert.equal(loanView({ ...QUOTE, monthly_instalment: null }).emi, null);
});

test("an event with no usable figures changes nothing", () => {
  for (const bad of [null, undefined, {}, { type: "loan" }, { project_cost: "1000000" }, { project_cost: NaN }, "loan"]) assert.equal(loanView(bad), null, String(bad));
});

test("free text in an event is shown as text and a missing value never prints as undefined or NaN", () => {
  const v = loanView({ ...QUOTE, business: "<img src=x onerror=1>", place: null, total_interest: undefined });
  assert.equal(v.where, "<img src=x onerror=1>");                                  // it is a string here; the page puts it in a text node
  assert.ok(!JSON.stringify(v).match(/undefined|NaN|null/));
  assert.match(script, /h\('div', 'loanwhere', v\.where\)/);
});

test("the panel is on the page, is always labelled indicative, resets for each call and speaks changes politely", () => {
  assert.match(html, /<section class="panel b-loan" aria-labelledby="h-loan">/);
  assert.match(html, /<span class="tag">indicative<\/span>/);
  assert.match(html, /id="loan" aria-live="polite"/);
  assert.match(script, /Indicative only\. These figures come from the scheme terms this project uses, not from a bank or the government\./);
  assert.match(script, /resetOrder\(\);\s*resetLoan\(\);/);
});

test("the panel does no arithmetic of its own", () => {
  const panel = script.slice(script.indexOf("/* ---- the loan quote so far"), script.indexOf("function resetLoan"));
  assert.doesNotMatch(panel, /[^/*]\s[*+\-/]\s\d|Math\./);
  assert.doesNotMatch(panel, /\.toFixed|parseFloat|reduce\(/);
});

test("the Auto-scroll switch only animates when motion is allowed, and the page's icons are hidden from assistive technology", () => {
  assert.doesNotMatch(html, /\.sw\{width:34px[^}]*transition/);          // the base rule has none; the one in the media query does
  assert.match(html, /@media \(prefers-reduced-motion:no-preference\)\{\.sw\{transition/);
  for (const s of [...html.matchAll(/<svg class="i"[^>]*>/g)].map(m => m[0])) assert.match(s, /aria-hidden="true"/, s);
});

test("at 200% zoom a panel's tag and the Auto-scroll switch drop under the title instead of leaving the screen", () => {
  assert.match(html, /\.ph\{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:6px 10px;/);
});

test("the call page's sticky header is solid, so the page scrolling under it never shows through", () => {
  assert.match(html, /header\{position:sticky;top:10px;[^}]*background:var\(--surface\);box-shadow:0 -10px 0 var\(--bg\)\}/);
});
