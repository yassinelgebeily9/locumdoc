// LocumDoc home page: drives the scroll story. Progressive enhancement only:
// without this script, or with reduced motion requested, every chapter is a
// normal, fully visible section.
(function () {
  if (!window.matchMedia || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  var root = document.documentElement;
  root.classList.add("js-cine");

  var wide = window.matchMedia("(min-width: 900px)");
  var open = document.querySelector('[data-cine="open"]');
  var tracks = [].slice.call(document.querySelectorAll('[data-cine="steps"]'));
  var path = document.querySelector('[data-cine="path"]');
  var header = document.querySelector(".site-header");
  var ticking = false;

  function clamp(x) { return x < 0 ? 0 : x > 1 ? 1 : x; }

  function update() {
    ticking = false;
    var vh = window.innerHeight;
    var hdr = header ? header.offsetHeight : 0;

    // opener drifts back as chapter one slides over it
    if (open) {
      var po = clamp(window.scrollY / (vh * 0.9));
      open.style.setProperty("--p", po.toFixed(3));
    }

    // pinned chapters: the scroll position inside the track picks the active step
    tracks.forEach(function (track) {
      var steps = track.querySelectorAll(".ch-step");
      if (!wide.matches) {
        for (var k = 0; k < steps.length; k++) steps[k].classList.add("on");
        return;
      }
      var r = track.getBoundingClientRect();
      var run = r.height - (vh - hdr);
      var p = run > 0 ? clamp((hdr - r.top) / run) : 0;
      var active = Math.min(steps.length - 1, Math.floor(p * steps.length));
      track.style.setProperty("--p", p.toFixed(3));
      for (var i = 0; i < steps.length; i++) steps[i].classList.toggle("on", i === active);
    });

    // licensing timeline draws itself as it scrolls through view
    if (path) {
      var rp = path.getBoundingClientRect();
      path.style.setProperty("--p", clamp((vh * 0.8 - rp.top) / rp.height).toFixed(3));
    }
  }

  function onScroll() {
    if (!ticking) { ticking = true; window.requestAnimationFrame(update); }
  }
  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", onScroll);
  if (wide.addEventListener) wide.addEventListener("change", onScroll);

  // sections fade up once as they enter the viewport
  var reveals = document.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
      });
    }, { rootMargin: "0px 0px -12% 0px", threshold: 0.12 });
    for (var j = 0; j < reveals.length; j++) io.observe(reveals[j]);
  } else {
    for (var q = 0; q < reveals.length; q++) reveals[q].classList.add("in");
  }

  // keyboard users who tab into a step see it, even if they did not scroll there
  tracks.forEach(function (track) {
    track.addEventListener("focusin", function (e) {
      var step = e.target.closest && e.target.closest(".ch-step");
      if (!step) return;
      var steps = track.querySelectorAll(".ch-step");
      for (var i = 0; i < steps.length; i++) steps[i].classList.toggle("on", steps[i] === step);
    });
  });

  update();
})();
