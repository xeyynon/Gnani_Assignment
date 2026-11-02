let nameTouched = false;
function fillTemplates(shopRows) {          // the "Start from" list: a blank shop, or a copy of any shop that exists
  const sel = $('add-template'), keep = sel.value;
  sel.replaceChildren(h('option', { value: 'blank', text: 'A blank shop (you add the stock and the knowledge)' }),
    ...shopRows.filter(s => s.state !== 'broken').map(s => h('option', { value: s.name, text: 'A copy of ' + s.title })));
  sel.value = [...sel.options].some(o => o.value === keep) ? keep : 'blank';
}
function checkAddName() {
  const name = $('add-name').value, bad = name ? shopIdProblem(name) : '';
  $('add-name').setAttribute('aria-invalid', String(!!bad));
  $('add-name-show').textContent = name || '...';
  say($('add-msg'), bad, bad ? 'bad' : '');
  return bad;
}
$('add-title').addEventListener('input', () => { if (!nameTouched) { $('add-name').value = slugify($('add-title').value); checkAddName(); } });
$('add-name').addEventListener('input', () => { nameTouched = true; checkAddName(); });
$('addform').addEventListener('submit', e => {
  e.preventDefault();
  const title = $('add-title').value.trim(), name = $('add-name').value, pin = $('add-pin').value.trim(), msg = $('add-msg');
  const bad = !title ? 'Give the shop a name people will recognise.' : shopIdProblem(name) || pinProblem(pin);
  if (bad) { say(msg, bad, 'bad'); return; }
  run($('add-go'), msg, 'Creating the shop...', async () => {
    const r = await adminCall('create_shop', { name, display_name: title, template: $('add-template').value, pin });
    $('add-result-title').textContent = title + ' is ready' + (r.pin_generated ? '' : ' with the PIN you chose');
    $('add-result-pin').textContent = r.pin;
    $('add-result-links').replaceChildren(
      h('a', { class: 'btn primary', href: '#edit/' + r.name }, icon('edit'), 'Edit the shop'),
      h('a', { class: 'btn', href: '/s/' + r.name + '/dashboard' }, 'Shop dashboard'),
      h('a', { class: 'btn', href: '/s/' + r.name + '/' }, 'Call page'));
    $('add-result').hidden = false;
    $('addform').reset(); nameTouched = false; $('add-name-show').textContent = '...';
    say(msg, '', '');
    await refreshNow();
  });
});
