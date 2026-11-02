function isPlainKey(e) {                       // a shortcut key press: no modifiers, not held down, not while typing
  if (!e || e.defaultPrevented || e.ctrlKey || e.metaKey || e.altKey || e.repeat) return false;
  const t = e.target, tag = t && t.tagName ? t.tagName.toLowerCase() : '';
  if (t && t.isContentEditable) return false;
  if (tag === 'textarea' || tag === 'select') return false;
  if (tag === 'input') return ['checkbox', 'radio', 'range', 'button', 'file', 'submit', 'reset'].includes(String(t.type || '').toLowerCase());
  return true;
}
