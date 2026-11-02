function skeletons(n, height) { return Array.from({ length: n }, () => h('div', { class: 'skel', style: 'height:' + height + 'px' })); }
