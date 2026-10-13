// Firebase Analytics, loaded only after the visitor chose "Accept analytics" in the cookie banner.
// The SDK is self-hosted (static/js/vendor, built from tools/firebase-sdk) so nothing loads before consent.
const CONSENT = "ld_consent";

function consent() {
  const m = document.cookie.match(/(?:^|; )ld_consent=([^;]*)/);
  return m ? decodeURIComponent(m[1]) : null;
}

function readJSON(id) {
  const el = document.getElementById(id);
  try { return el ? JSON.parse(el.textContent) : null; } catch (e) { return null; }
}

// Removes Google Analytics cookies when someone switches to "Essential only".
function clearAnalyticsCookies() {
  const host = location.hostname.split(".");
  const domains = [""];
  for (let i = 0; i < host.length - 1; i++) domains.push("; domain=." + host.slice(i).join("."));
  document.cookie.split("; ").map((c) => c.split("=")[0]).filter((n) => /^_ga/.test(n)).forEach((name) => {
    domains.forEach((d) => { document.cookie = name + "=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/" + d; });
  });
}

let started = false;
async function start() {
  if (started) return;
  const config = readJSON("ld-analytics-config");
  if (!config) return;
  started = true;
  try {
    const sdk = await import("./vendor/firebase-analytics.js");
    if (!(await sdk.isSupported())) return;
    const app = sdk.initializeApp(config);
    const analytics = sdk.initializeAnalytics(app, {
      config: {
        cookie_expires: 15552000,               // 6 months, as stated on the cookie settings page
        cookie_flags: "SameSite=Lax;Secure",
        allow_google_signals: false,            // no cross-device advertising features
        allow_ad_personalization_signals: false,
        page_title: document.title,
        language: document.documentElement.lang,
      },
    });
    (readJSON("ld-analytics-events") || []).forEach((ev) => sdk.logEvent(analytics, ev.name, ev.params || {}));
  } catch (e) {
    // Analytics must never break the site (blocked by an extension, offline, etc.).
  }
}

if (consent() === "analytics") start();
else if (consent() === "essential") clearAnalyticsCookies();

document.addEventListener("ld:consent", (e) => {
  if (e.detail === "analytics") start();
  else clearAnalyticsCookies();
});
