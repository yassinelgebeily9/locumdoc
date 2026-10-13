// Progressive enhancement only — every page works without JavaScript.
(function () {
  var header = document.querySelector(".site-header");
  var toggle = document.querySelector(".menu-toggle");
  if (header && toggle) {
    toggle.addEventListener("click", function () {
      var open = header.classList.toggle("nav-open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }

  // Confirm destructive actions: <form data-confirm="Are you sure?">
  document.querySelectorAll("form[data-confirm]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      if (!window.confirm(form.getAttribute("data-confirm"))) e.preventDefault();
    });
  });

  // Auto-submit small status selects: <select data-autosubmit>
  document.querySelectorAll("select[data-autosubmit]").forEach(function (sel) {
    sel.addEventListener("change", function () { sel.form.submit(); });
    var btn = sel.form.querySelector("[data-autosubmit-btn]");
    if (btn) btn.hidden = true;
  });

  // Keep the job end date after the start date.
  var start = document.querySelector("input[name=start_date]");
  var end = document.querySelector("input[name=end_date]");
  if (start && end) {
    start.addEventListener("change", function () { end.min = start.value; });
  }
  var from = document.querySelector("input[name=available_from]");
  var to = document.querySelector("input[name=available_to]");
  if (from && to) {
    from.addEventListener("change", function () { to.min = from.value; });
  }

  // ---- Loading states: once a form is sent, show it and block a second click.
  // Runs after the confirm() handlers above, so a cancelled confirm leaves the form alone.
  var root = document.documentElement;
  root.classList.add("js");
  var defaultBusy = root.getAttribute("data-loading-text") || "…";
  document.addEventListener("submit", function (e) {
    var form = e.target;
    if (e.defaultPrevented || form.hasAttribute("data-no-loading") || form.hasAttribute("data-cookie-form")) return;
    if (form.getAttribute("aria-busy") === "true") { e.preventDefault(); return; }
    form.setAttribute("aria-busy", "true");
    var btn = e.submitter || form.querySelector("button[type=submit], button:not([type])");
    if (btn) {
      btn.setAttribute("data-label", btn.innerHTML);
      btn.classList.add("is-loading");
      btn.textContent = btn.getAttribute("data-loading") || defaultBusy;
    }
    // Disable after the browser has read the clicked button's name/value into the submission.
    setTimeout(function () {
      form.querySelectorAll("button[type=submit], button:not([type])").forEach(function (b) { b.disabled = true; });
    }, 0);
  });
  // Coming back with the Back button restores the page as it was: undo the loading state.
  window.addEventListener("pageshow", function (e) {
    if (!e.persisted) return;
    document.querySelectorAll("form[aria-busy=true]").forEach(function (form) {
      form.removeAttribute("aria-busy");
      form.querySelectorAll("button").forEach(function (b) {
        b.disabled = false;
        if (b.hasAttribute("data-label")) { b.innerHTML = b.getAttribute("data-label"); b.classList.remove("is-loading"); }
      });
    });
  });

  // ---- Error states: move focus to the list of problems so screen readers announce it.
  var summary = document.querySelector("[data-error-summary]");
  if (summary) summary.focus();

  // ---- PDF uploads: catch the wrong file type or size before a slow upload.
  document.querySelectorAll("input[data-pdf-only]").forEach(function (input) {
    var err = document.getElementById(input.id + "-error");
    function check() {
      var f = input.files && input.files[0], msg = "";
      if (f && !/\.pdf$/i.test(f.name)) msg = input.getAttribute("data-msg-type");
      else if (f && f.size > +input.getAttribute("data-max-bytes")) msg = input.getAttribute("data-msg-size");
      input.setCustomValidity(msg);
      input.setAttribute("aria-invalid", msg ? "true" : "false");
      if (err) { err.textContent = msg; err.hidden = !msg; }
      input.closest(".field").classList.toggle("has-error", !!msg);
      return !msg;
    }
    input.addEventListener("change", check);
    input.form.addEventListener("submit", function (e) { if (!check()) { e.preventDefault(); input.focus(); } }, true);
  });

  // ---- Sticky call to action on phones: hidden while the page's own main button is on screen.
  var sticky = document.querySelector("[data-sticky-cta]");
  var heroes = document.querySelectorAll("[data-hero-cta]");
  if (sticky && heroes.length && "IntersectionObserver" in window) {
    var visible = new Set();
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) { if (en.isIntersecting) visible.add(en.target); else visible.delete(en.target); });
      sticky.classList.toggle("is-tucked", visible.size > 0);
    });
    heroes.forEach(function (h) { io.observe(h); });
  }

  // ---- Cookie banner: save the choice without leaving the page.
  var banner = document.querySelector("[data-cookie-banner]");
  document.querySelectorAll("form[data-cookie-form]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      if (!window.fetch || !banner || !banner.contains(form)) return;  // the settings page reloads normally
      e.preventDefault();
      var choice = (e.submitter && e.submitter.value) || "essential";
      var data = new FormData(form);
      data.set("choice", choice);
      fetch(form.action, { method: "POST", body: data, credentials: "same-origin",
                           headers: { "X-Requested-With": "fetch" } })
        .then(function (r) {
          if (!r.ok) throw new Error(r.status);
          banner.hidden = true;
          document.dispatchEvent(new CustomEvent("ld:consent", { detail: choice }));
        })
        .catch(function () { form.submit(); });
    });
  });
})();
