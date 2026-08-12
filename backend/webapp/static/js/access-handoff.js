(async function redeemHandoff() {
  let token = window.location.hash.startsWith("#")
    ? window.location.hash.slice(1)
    : "";
  window.history.replaceState(null, "", "/access-handoff");
  const status = document.getElementById("handoff-status");
  if (!token) {
    status.textContent = "This Review Lab link is invalid or expired.";
    return;
  }
  let response;
  try {
    response = await fetch("/api/browser-handoffs/redeem", {
      method: "POST",
      credentials: "same-origin",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({token: token}),
    });
  } catch (_error) {
    response = null;
  }
  token = "";
  if (!response || !response.ok) {
    status.textContent = "This Review Lab link is invalid or expired.";
    return;
  }
  window.location.replace("/review-lab");
}());
