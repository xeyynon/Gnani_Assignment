/* Everything on a page is built from text nodes, never from HTML strings: it is what a caller said or a
   shopkeeper's customer is called, and must not be able to inject markup.
   h('div', 'class names', 'text')   or   h('div', { class: 'x', text: 'y', 'data-id': 3 }, child, child) */
const $ = id => document.getElementById(id);
function h(tag, attrs) {
  const e = document.createElement(tag);
  if (typeof attrs === 'string') e.className = attrs;
  else for (const k in (attrs || {})) {
    if (k === 'class') e.className = attrs[k];
    else if (k === 'text') e.textContent = attrs[k];
    else e.setAttribute(k, attrs[k]);
  }
  for (let i = 2; i < arguments.length; i++) {
    const c = arguments[i];
    if (c == null || c === false) continue;
    e.appendChild(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return e;
}
const SVG = document.querySelector('svg').namespaceURI;     // the icon sheet's own, so no address is written here
function icon(name) {
  const s = document.createElementNS(SVG, 'svg'); s.setAttribute('class', 'i');
  const u = document.createElementNS(SVG, 'use'); u.setAttribute('href', '#i-' + name); s.appendChild(u);
  return s;
}
