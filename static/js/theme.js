// Tema claro, oscuro o el del sistema. Al cambiar, el tema nuevo se abre en círculo desde el botón
// (View Transitions API); en navegadores sin esa API el cambio es inmediato.
(function () {
  "use strict";
  var root = document.documentElement;
  var buttons = Array.prototype.slice.call(document.querySelectorAll("[data-theme-choice]"));
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function current() {
    try { return localStorage.getItem("sgsi-theme") || "system"; } catch (e) { return "system"; }
  }
  function mark(choice) {
    buttons.forEach(function (b) { b.setAttribute("aria-pressed", String(b.dataset.themeChoice === choice)); });
  }
  function apply(choice) {
    if (choice === "light" || choice === "dark") root.dataset.theme = choice;
    else delete root.dataset.theme;
    try { choice === "system" ? localStorage.removeItem("sgsi-theme") : localStorage.setItem("sgsi-theme", choice); } catch (e) { /* sin almacenamiento */ }
    mark(choice);
  }

  buttons.forEach(function (button) {
    button.addEventListener("click", function () {
      var choice = button.dataset.themeChoice;
      if (choice === current()) return;
      if (!document.startViewTransition || reduce) { apply(choice); return; }
      var r = button.getBoundingClientRect();
      var x = r.left + r.width / 2;
      var y = r.top + r.height / 2;
      root.style.setProperty("--vt-x", x + "px");
      root.style.setProperty("--vt-y", y + "px");
      root.style.setProperty("--vt-r", Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y)) + "px");
      document.startViewTransition(function () { apply(choice); });
    });
  });
  mark(current());
})();
