function emptyCard(spec) {                    // {title, text, action?}: say what is missing, what will appear, and one way to start
  return h('div', { class: 'empty' }, h('strong', { class: 'et', text: spec.title }), h('span', { text: spec.text }),
    spec.action ? h('a', { class: 'link', href: callPageUrl(location.pathname), text: spec.action }) : null);
}
function fill(id, items, make, empty) {          // empty is a plain sentence (the admin) or a {title, text, action} (the dashboard)
  $(id).replaceChildren(...(items.length ? items.map(make) : [typeof empty === 'string' ? h('div', { class: 'empty', text: empty }) : emptyCard(empty)]));
}
