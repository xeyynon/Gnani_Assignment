function skeletons(n, height) { return Array.from({ length: n }, () => h('div', { class: 'skel', style: 'height:' + height + 'px' })); }
function renderLoading() {                       // "loading" must not look like "nothing here"
  $('tiles').replaceChildren(...skeletons(3, 78));
  ['recent', 'attn', 'orders', 'ledger', 'loans'].forEach(id => $(id).replaceChildren(...skeletons(3, 54)));
  $('trend').replaceChildren(...skeletons(7, 120));
  document.querySelector('main').setAttribute('aria-busy', 'true');
}
