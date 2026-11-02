const STATE = { ready: ['confirmed', 'Ready'], attention: ['credit_pending', 'Needs attention'], broken: ['incomplete', 'Broken'] };
function stateView(s) { return STATE[s] || STATE.attention; }              // [pill class, label]; an unknown state is never shown as ready
function severityView(s) { return s === 'error' ? ['incomplete', 'Error'] : ['credit_pending', 'Warning']; }
function plural(n, one, many) { return n + ' ' + (n === 1 ? one : many); }
function liveText(seconds) {                // [secs, ...] -> the line for one shop or the whole install
  if (!seconds || !seconds.length) return 'No call right now';
  const s = seconds[0], t = Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0');
  return (seconds.length > 1 ? seconds.length + ' calls' : 'A customer is on a call') + ' (' + t + ')';
}
function shopSub(totals) {                  // the line under the "Shops" tile
  if (!totals.shops) return 'none yet';
  const bits = [totals.shops_ready + ' ready'];
  if (totals.shops_attention) bits.push(totals.shops_attention + ' need attention');
  if (totals.shops_broken) bits.push(totals.shops_broken + ' broken');
  return bits.join(', ');
}
function problemSub(totals) {               // the line under the "To fix" tile
  if (!totals.errors && !totals.warnings) return 'nothing wrong';
  const bits = [];
  if (totals.errors) bits.push(plural(totals.errors, 'error', 'errors'));
  if (totals.warnings) bits.push(plural(totals.warnings, 'warning', 'warnings'));
  return bits.join(', ');
}

/* what a shop's link name may be: the same rule as the server (shops.py), checked here only to help the typist */
const SHOP_ID = /^[a-z0-9][a-z0-9_-]{1,39}$/;
function validShopId(s) { return SHOP_ID.test(String(s == null ? '' : s)); }
function slugify(title) {                   // "Sri Lakshmi Kirana" -> "sri_lakshmi_kirana"
  return String(title == null ? '' : title).toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 40).replace(/_+$/, '');
}
function shopIdProblem(s) {                 // '' when fine, else what to tell the typist
  s = String(s == null ? '' : s);
  if (!s) return 'Give the shop a link name.';
  if (!validShopId(s)) return 'Use lower case letters, digits, - and _ (2 to 40 characters), starting with a letter or digit.';
  return '';
}
function pinProblem(pin) {                  // an empty PIN is fine (one is made); a typed one must be long enough
  pin = String(pin == null ? '' : pin);
  return pin && pin.length < 4 ? 'A PIN needs at least 4 characters.' : '';
}
function parseAliases(text) {               // "Rice, chawal, rice" -> ["rice", "chawal"]
  return [...new Set(String(text == null ? '' : text).split(',').map(a => a.trim().toLowerCase()).filter(Boolean))];
}
const STOCK_UNITS = ['kg', 'litre', 'packet', 'piece', 'bar', 'bottle', 'bag', 'loaf'];     // the same list as stock.py
function newItem(f) {                       // the form's fields -> an item for stock.json (the server validates it again)
  const unit = String(f.unit || '');
  return {
    sku: String(f.sku || '').trim().toUpperCase(), category: 'other', unit, price: Number(f.price), in_stock: true,
    name: { en: String(f.en || '').trim(), hi: String(f.hi || '').trim(), te: String(f.te || '').trim() },
    pack: 'per ' + unit, aliases: parseAliases(f.aliases)
  };
}
function newItemProblem(item) {             // '' when it looks complete; the server has the final say
  if (!/^[A-Z0-9][A-Z0-9-]{1,30}$/.test(item.sku)) return 'The item code uses capital letters, digits and - (for example SUGAR-1KG).';
  if (!item.name.en || !item.name.hi || !item.name.te) return 'Give the name in English, Hindi and Telugu: callers use all three.';
  if (!STOCK_UNITS.includes(item.unit)) return 'Pick a unit.';
  if (!(item.price > 0)) return 'The price must be a number above zero.';
  if (!item.aliases.length) return 'Add at least one way callers say it in English letters, for example "sugar, cheeni".';
  return '';
}
function stockChanges(original, edited) {   // what changed in the stock table -> {update, remove, bad}
  const was = new Map(original.map(i => [i.sku, i]));
  const update = [], remove = [], bad = [];
  edited.forEach(e => {
    const o = was.get(e.sku);
    if (!o) return;
    if (e.remove) { remove.push(e.sku); return; }
    const change = { sku: e.sku };
    if (!(e.price > 0)) { bad.push(e.sku); return; }
    if (e.price !== o.price) change.price = e.price;
    if (e.in_stock !== o.in_stock) change.in_stock = e.in_stock;
    if (Object.keys(change).length > 1) update.push(change);
  });
  return { update, remove, bad };
}
function changeSummary(c) {                 // "2 prices or availability changed, 1 removed"
  const bits = [];
  if (c.update.length) bits.push(plural(c.update.length, 'item changed', 'items changed'));
  if (c.remove.length) bits.push(c.remove.length + ' removed');
  return bits.join(', ');
}
