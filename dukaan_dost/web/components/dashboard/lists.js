function fill(id, items, make, emptyText) {
  $(id).replaceChildren(...(items.length ? items.map(make) : [h('div', { class: 'empty', text: emptyText })]));
}
