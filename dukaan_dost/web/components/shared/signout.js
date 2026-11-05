/* ---- sign out: end this browser's session on the server, then reload (the same address now shows the sign-in page) ---- */
$('signout').addEventListener('click', async () => {
  $('signout').disabled = true;
  try { await fetch(location.pathname.replace(/\/$/, '') + '/signout', { cache: 'no-store', credentials: 'same-origin' }); } catch (e) { /* offline: the reload below says so */ }
  location.reload();
});
