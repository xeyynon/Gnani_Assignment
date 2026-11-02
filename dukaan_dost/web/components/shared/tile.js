function tile(iconName, tone, key, value, sub, subCls, cls) {
  return h('div', { class: 'tile' + (cls ? ' ' + cls : '') },
    h('div', { class: 'ico ' + tone }, icon(iconName)),
    h('div', null, h('div', { class: 'k', text: key }), h('div', { class: 'v', text: value }), sub ? h('div', { class: 's' + (subCls ? ' ' + subCls : ''), text: sub }) : null));
}
