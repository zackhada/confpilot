// Applies the saved theme before first paint so the page never flashes the wrong one.
// Kept as a tiny external file so a strict Content-Security-Policy needs no inline script.
(function () {
  try {
    var saved = window.localStorage.getItem('confpilot.theme')
    if (saved === 'light' || saved === 'dark') {
      document.documentElement.setAttribute('data-theme', saved)
    }
  } catch (_err) {
    // Storage can be blocked in private windows; the dark default stays.
  }
})()
