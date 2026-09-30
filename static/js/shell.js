// Menú lateral: plegado en escritorio (se recuerda), deslizable en pantallas angostas,
// y marca la página actual.
(function () {
  "use strict";
  var body = document.body;
  var toggle = document.querySelector("[data-nav-toggle]");
  var scrim = document.querySelector("[data-nav-scrim]");
  var groups = Array.prototype.slice.call(document.querySelectorAll("[data-nav-group]"));
  var narrow = function () { return window.matchMedia("(max-width: 900px)").matches; };

  function save(value) { try { localStorage.setItem("sgsi-nav", value); } catch (e) { /* sin almacenamiento */ } }

  function sync() {
    var expanded = narrow() ? body.classList.contains("nav-open") : !body.classList.contains("nav-collapsed");
    if (toggle) toggle.setAttribute("aria-expanded", String(expanded));
  }

  function closeMobile() {
    body.classList.remove("nav-open");
    if (scrim) { scrim.classList.remove("is-visible"); setTimeout(function () { scrim.hidden = true; }, 200); }
    sync();
  }

  if (toggle) {
    toggle.addEventListener("click", function () {
      if (narrow()) {
        if (body.classList.contains("nav-open")) { closeMobile(); return; }
        body.classList.add("nav-open");
        if (scrim) { scrim.hidden = false; requestAnimationFrame(function () { scrim.classList.add("is-visible"); }); }
      } else {
        var collapsed = body.classList.toggle("nav-collapsed");
        save(collapsed ? "collapsed" : "open");
        if (collapsed) groups.forEach(function (g) { g.open = false; });
      }
      sync();
    });
  }
  if (scrim) scrim.addEventListener("click", closeMobile);
  document.addEventListener("keydown", function (e) { if (e.key === "Escape" && body.classList.contains("nav-open")) closeMobile(); });

  // Con el menú reducido, un clic en una cláusula lo vuelve a abrir para mostrar sus numerales.
  groups.forEach(function (group) {
    group.querySelector("summary").addEventListener("click", function () {
      if (body.classList.contains("nav-collapsed") && !narrow()) {
        body.classList.remove("nav-collapsed");
        save("open");
        sync();
      }
    });
  });

  // Página actual: resalta el enlace y abre su cláusula.
  var path = window.location.pathname;
  var links = Array.prototype.slice.call(document.querySelectorAll(".nav-link[href], .nav-sub a[href]"));
  var best = null;
  links.forEach(function (a) {
    var href = a.getAttribute("href");
    if (href && href !== "/" && path.indexOf(href) === 0 && (!best || href.length > best.getAttribute("href").length)) best = a;
  });
  if (best) {
    best.classList.add("is-current");
    best.setAttribute("aria-current", "page");
    var group = best.closest("[data-nav-group]");
    if (group && !body.classList.contains("nav-collapsed")) group.open = true;
  }
  sync();
})();
