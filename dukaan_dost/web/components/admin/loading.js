function renderLoading() {                       // "loading" must not look like "nothing here"
  $('tiles').replaceChildren(...skeletons(4, 78));
  ['shops', 'problems', 'solved'].forEach(id => $(id).replaceChildren(...skeletons(3, 70)));
  document.querySelector('main').setAttribute('aria-busy', 'true');
}
