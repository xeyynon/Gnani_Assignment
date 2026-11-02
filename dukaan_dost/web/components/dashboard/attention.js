function renderAttention(list) {
  $('attncount').textContent = String(list.length); $('attncount').hidden = !list.length;   // the count that used to be a tile of its own
  if (!list.length) { $('attn').replaceChildren(h('div', { class: 'empty', text: 'Nothing needs you right now.' })); return; }
  $('attn').replaceChildren(...list.slice(0, 6).map(a => h('div', { class: 'alert' },
    h('div', { class: 'ico ' + a.kind }, icon('alert')), h('span', { class: 't', text: a.title }), h('span', { class: 'tag2 ' + a.kind, text: a.tag }))));
}
