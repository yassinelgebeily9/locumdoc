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

  // On phones, fold the secondary job filters behind a "More filters" button
  // unless one of them is already in use.
  var filters = document.querySelector("form[data-collapsible]");
  var ftoggle = filters && filters.querySelector(".filter-toggle");
  if (filters && ftoggle && window.matchMedia("(max-width: 560px)").matches) {
    var inUse = Array.prototype.some.call(filters.querySelectorAll(".opt-filter select"), function (s) { return s.value; });
    var setOpen = function (open) {
      filters.classList.toggle("collapsed", !open);
      ftoggle.setAttribute("aria-expanded", open ? "true" : "false");
    };
    setOpen(inUse);
    ftoggle.addEventListener("click", function () { setOpen(filters.classList.contains("collapsed")); });
  }

  // On phones, show the first twelve specialties and a button for the rest.
  var cloud = document.querySelector("[data-foldable]");
  var more = document.querySelector(".spec-more");
  if (cloud && more && window.matchMedia("(max-width: 560px)").matches) {
    cloud.classList.add("folded");
    more.hidden = false;
    more.setAttribute("aria-expanded", "false");
    more.addEventListener("click", function () {
      cloud.classList.remove("folded");
      more.hidden = true;
      more.setAttribute("aria-expanded", "true");
      var next = cloud.querySelectorAll("a")[12];
      if (next) next.focus();
    });
  }

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
})();
