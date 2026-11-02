let editing = null;                         // {name, stock: [{sku, price, in_stock}], rows: [{sku, price, stock, remove}]}
$('it-unit').replaceChildren(h('option', { value: '', text: 'Choose...' }), ...STOCK_UNITS.map(u => h('option', { value: u, text: u })));

function stockRow(item, rows) {
  const price = h('input', { type: 'number', min: '0', step: 'any', inputmode: 'decimal', 'aria-label': 'Price of ' + item.name });
  price.value = item.price;
  const stock = h('input', { type: 'checkbox', 'aria-label': item.name + ' is in stock' }); stock.checked = !!item.in_stock;
  const remove = h('input', { type: 'checkbox', 'aria-label': 'Remove ' + item.name });
  rows.push({ sku: item.sku, price, stock, remove });
  return h('tr', null,
    h('td', null, h('div', { class: 'who', text: item.name || item.sku }), h('div', { class: 'muted', text: item.sku + ', per ' + item.unit })),
    h('td', null, price), h('td', null, stock), h('td', null, remove));
}

function fillEditor(s) {
  const rows = [];
  editing = { name: s.name, stock: s.stock.map(i => ({ sku: i.sku, price: i.price, in_stock: i.in_stock })), rows };
  $('edit-title').textContent = s.display_name;
  document.title = s.display_name + ': admin';
  $('edit-links').replaceChildren(
    ' | ', h('a', { href: '/s/' + s.name + '/dashboard', text: 'Shop dashboard' }),
    ' | ', h('a', { href: '/s/' + s.name + '/', text: 'Call page' }));
  $('ed-title').value = s.display_name;
  $('ed-prompt').value = s.system_prompt;
  $('ed-stock').replaceChildren(...(s.stock.length ? s.stock.map(i => stockRow(i, rows))
    : [h('tr', null, h('td', { colspan: '4', class: 'empty', text: 'No items yet. Add the first one below.' }))]));
}

async function openEditor(name) {
  editing = null;
  $('edit-title').textContent = 'Loading...';
  ['ed-msg', 'ed-pin-msg', 'ed-stock-msg', 'it-msg'].forEach(id => say($(id), ''));
  $('ed-pin-result').hidden = true; $('ed-pin').value = '';
  try { fillEditor(await adminCall('get_shop', { shop: name })); }
  catch (e) { $('edit-title').textContent = 'Could not open this shop'; say($('ed-msg'), e.message, 'bad'); }
}

$('ed-save').addEventListener('click', () => {
  if (!editing) return;
  run($('ed-save'), $('ed-msg'), 'Saving...', async () => {
    const r = await adminCall('save_prompt', { shop: editing.name, display_name: $('ed-title').value, system_prompt: $('ed-prompt').value });
    $('edit-title').textContent = r.display_name;
    say($('ed-msg'), 'Saved. The next call will use it.', 'good');
    await refreshNow();
  });
});

$('ed-setpin').addEventListener('click', () => {
  if (!editing) return;
  const pin = $('ed-pin').value.trim(), bad = pinProblem(pin);
  if (bad) { say($('ed-pin-msg'), bad, 'bad'); return; }
  run($('ed-setpin'), $('ed-pin-msg'), 'Setting the PIN...', async () => {
    const r = await adminCall('set_pin', { shop: editing.name, pin });
    $('ed-pin-show').textContent = r.pin; $('ed-pin-result').hidden = false; $('ed-pin').value = '';
    say($('ed-pin-msg'), r.pin_generated ? 'A new PIN was made. The old one no longer works.' : 'The PIN was set. The old one no longer works.', 'good');
    await refreshNow();
  });
});

$('ed-stock-save').addEventListener('click', () => {
  if (!editing) return;
  const edited = editing.rows.map(r => ({ sku: r.sku, price: r.price.value === '' ? NaN : Number(r.price.value), in_stock: r.stock.checked, remove: r.remove.checked }));
  const c = stockChanges(editing.stock, edited);
  if (c.bad.length) { say($('ed-stock-msg'), 'The price of ' + c.bad.join(', ') + ' must be a number above zero.', 'bad'); return; }
  if (!c.update.length && !c.remove.length) { say($('ed-stock-msg'), 'Nothing has changed.'); return; }
  run($('ed-stock-save'), $('ed-stock-msg'), 'Saving...', async () => {
    await adminCall('save_stock', { shop: editing.name, update: c.update, remove: c.remove });
    const name = editing.name;
    await openEditor(name);
    say($('ed-stock-msg'), 'Saved: ' + changeSummary(c) + '. The knowledge file was rewritten from it.', 'good');
  });
});

$('itemform').addEventListener('submit', e => {
  e.preventDefault();
  if (!editing) return;
  const item = newItem({ sku: $('it-sku').value, en: $('it-en').value, hi: $('it-hi').value, te: $('it-te').value,
    unit: $('it-unit').value, price: $('it-price').value, aliases: $('it-aliases').value });
  const bad = newItemProblem(item);
  if (bad) { say($('it-msg'), bad, 'bad'); return; }
  run($('it-add'), $('it-msg'), 'Adding...', async () => {
    await adminCall('save_stock', { shop: editing.name, add: [item] });
    const name = editing.name;
    $('itemform').reset();
    await openEditor(name);
    say($('it-msg'), item.name.en + ' was added.', 'good');
  });
});
