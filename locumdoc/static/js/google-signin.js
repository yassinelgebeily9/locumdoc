// "Continue with Google": Firebase Authentication opens Google's sign-in window, then we hand the
// resulting ID token to the server, which checks it and logs the person in (or finishes their sign-up).
// The self-hosted Firebase SDK is set up as soon as a sign-in page opens, so the Google window can open
// the moment the button is clicked (Safari blocks pop-ups that open later than that). Firebase keeps no
// session of its own here (in-memory persistence): the site's normal login takes over.
const box = document.querySelector("[data-google-signin]");

function readConfig() {
  try { return JSON.parse(document.getElementById("ld-firebase-config").textContent); } catch (e) { return null; }
}

let fb = null;  // { sdk, auth, provider } once ready
const ready = box && readConfig() ? import("./vendor/firebase-auth.js").then((sdk) => {
  const app = sdk.initializeApp(readConfig(), "locumdoc-signin");
  const auth = sdk.initializeAuth(app, {
    persistence: sdk.inMemoryPersistence,
    popupRedirectResolver: sdk.browserPopupRedirectResolver,
  });
  const provider = new sdk.GoogleAuthProvider();
  provider.setCustomParameters({ prompt: "select_account" });
  fb = { sdk, auth, provider };
  return fb;
}).catch(() => null) : Promise.resolve(null);

if (box) {
  const button = box.querySelector("button");
  const errorEl = box.querySelector("[data-google-error]");
  const label = button.innerHTML;

  const busy = (on) => {
    button.disabled = on;
    button.classList.toggle("is-loading", on);
    if (on) button.textContent = button.getAttribute("data-loading");
    else button.innerHTML = label;
  };
  const showError = (msg) => { errorEl.textContent = msg; errorEl.hidden = !msg; };

  button.addEventListener("click", async () => {
    showError("");
    // Start the pop-up straight from the click when Firebase is ready (the usual case).
    const popup = fb ? fb.sdk.signInWithPopup(fb.auth, fb.provider) : null;
    busy(true);
    try {
      const f = fb || (await ready);
      if (!f) throw new Error("unavailable");
      const result = await (popup || f.sdk.signInWithPopup(f.auth, f.provider));
      const token = await result.user.getIdToken();
      await f.sdk.signOut(f.auth);

      const body = new URLSearchParams({
        id_token: token,
        intent: box.dataset.intent || "login",
        next: box.dataset.next || "",
        csrf_token: box.dataset.csrf,
      });
      const res = await fetch(box.dataset.endpoint, { method: "POST", body, credentials: "same-origin" });
      const data = await res.json().catch(() => ({}));
      if (res.ok && data.redirect) {
        window.location.assign(data.redirect);
        return;
      }
      showError(data.error || box.dataset.msgFailed);
    } catch (e) {
      const code = (e && e.code) || "";
      if (code === "auth/popup-closed-by-user" || code === "auth/cancelled-popup-request") {
        // they closed the Google window: nothing to report
      } else if (code === "auth/popup-blocked") {
        showError(box.dataset.msgBlocked);
      } else {
        showError(box.dataset.msgFailed);
      }
    }
    busy(false);
  });
}
