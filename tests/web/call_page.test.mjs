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
const { langName, clock, rupees, barHeight, nextTheme, themeLabel, isPlainKey } = new Function(
  `${helperSource}; return { langName, clock, rupees, barHeight, nextTheme, themeLabel, isPlainKey };`)();

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
  for (const type of ["ready", "busy", "stop", "user", "agent", "order"]) {
    assert.match(script, new RegExp(`m\.type === '${type}'`), `no handler for ${type}`);
  }
});

// ---- rules both pages follow ----
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
