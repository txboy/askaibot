const VALID = ['warm', 'cool', 'tech']

export function applyTheme(theme) {
  const t = VALID.includes(theme) ? theme : 'warm'
  document.documentElement.setAttribute('data-theme', t)
}
