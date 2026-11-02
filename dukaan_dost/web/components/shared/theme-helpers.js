function nextTheme(t) { const o = ['auto', 'light', 'dark']; return o[(o.indexOf(t) + 1) % o.length] || 'auto'; }
function themeLabel(t) { return { auto: 'Auto', light: 'Light', dark: 'Dark' }[t] || 'Auto'; }
