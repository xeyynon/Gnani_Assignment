function renderTiles(t) {
  $('tiles').replaceChildren(
    tile('store', 'blue', 'Shops', String(t.shops), shopSub(t), t.shops_broken ? 'down' : '', 'hero brut'),
    tile('phone', 'green', 'Calls now', String(t.live_calls), t.live_calls ? 'a customer is on a call' : 'no call right now'),
    tile('alert', t.errors ? 'warn' : 'amber', 'To fix', String(t.errors + t.warnings), problemSub(t)),
    tile('cart', 'green', 'Orders today', String(t.orders_today), 'across all shops'));
}
