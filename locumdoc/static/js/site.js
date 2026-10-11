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
})();
