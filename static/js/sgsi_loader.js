// Cargador SGSI. Usa Lottie si static/vendor/lottie_light.min.js existe; si no, queda el SVG animado.
(function () {
  "use strict";

  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var config = document.querySelector("[data-sgsi-loader-config]");
  var libUrl = config && config.dataset.lottieLib;
  var animUrl = config && config.dataset.lottieSrc;
  var libPromise = null;

  function loadLibrary() {
    if (window.lottie) return Promise.resolve(window.lottie);
    if (!libUrl) return Promise.reject(new Error("sin librería"));
    if (!libPromise) {
      libPromise = new Promise(function (resolve, reject) {
        var script = document.createElement("script");
        script.src = libUrl;
        script.async = true;
        script.onload = function () { window.lottie ? resolve(window.lottie) : reject(new Error("lottie ausente")); };
        script.onerror = reject;
        document.head.appendChild(script);
      });
    }
    return libPromise;
  }

  function mount(loader) {
    if (!loader || loader.dataset.mounted) return;
    loader.dataset.mounted = "1";
    var box = loader.querySelector("[data-lottie-player]");
    if (!box || !animUrl) return;
    loadLibrary().then(function (lottie) {
      var anim = lottie.loadAnimation({
        container: box, renderer: "svg", loop: !reduce, autoplay: !reduce, path: animUrl
      });
      anim.addEventListener("DOMLoaded", function () {
        loader.classList.add("has-lottie");
        if (reduce) anim.goToAndStop(60, true);
      });
    }).catch(function () { /* se mantiene el SVG de respaldo */ });
  }

  document.querySelectorAll("[data-sgsi-loader]").forEach(function (el) {
    if (!el.hasAttribute("data-sgsi-page-loader")) mount(el);
  });

  var overlay = document.querySelector("[data-sgsi-page-loader]");
  var bar = document.querySelector("[data-nav-progress]");
  var timer = null;
  var safety = null;

  // Al cambiar de página se muestra la pantalla con los discos de SiempreSoft.
  // Espera 200 ms para no parpadear cuando la página siguiente carga al instante.
  function show() {
    if (!overlay) return;
    clearTimeout(timer);
    timer = setTimeout(function () {
      mount(overlay);
      overlay.hidden = false;
      window.requestAnimationFrame(function () { overlay.classList.add("is-visible"); });
      clearTimeout(safety);
      safety = setTimeout(hide, 12000);
    }, 200);
  }

  function hide() {
    clearTimeout(timer);
    clearTimeout(safety);
    if (bar && bar.classList.contains("is-active")) {
      bar.classList.remove("is-active");
      bar.classList.add("is-done");
      setTimeout(function () { bar.classList.remove("is-done"); }, 350);
    }
    document.querySelectorAll(".is-busy").forEach(function (b) { b.classList.remove("is-busy"); b.removeAttribute("aria-busy"); });
    if (!overlay) return;
    overlay.classList.remove("is-visible");
    overlay.hidden = true;
  }

  var DOWNLOAD = /\/(descargar|download|docx|firmada|ver)\/?$/i;

  document.addEventListener("click", function (event) {
    if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    var link = event.target.closest("a[href]");
    if (!link) return;
    var href = link.getAttribute("href") || "";
    if (!href || href.charAt(0) === "#" || link.target === "_blank" || link.hasAttribute("download") || link.hasAttribute("data-no-loader")) return;
    if (/^(javascript|mailto|tel):/i.test(href)) return;
    var url = new URL(link.href, window.location.href);
    if (url.origin !== window.location.origin || DOWNLOAD.test(url.pathname)) return;
    if (url.pathname === window.location.pathname && url.search === window.location.search) return;
    show();
  });

  document.addEventListener("submit", function (event) {
    var form = event.target;
    if (event.defaultPrevented || form.target === "_blank" || form.hasAttribute("data-no-loader")) return;
    var action = form.getAttribute("action") || "";
    if (DOWNLOAD.test(action)) return;
    var button = event.submitter || form.querySelector("[type=submit]");
    if (button) { button.classList.add("is-busy"); button.setAttribute("aria-busy", "true"); }
    show();
  });

  window.addEventListener("pageshow", hide);
  window.SGSILoader = { show: show, hide: hide, mount: mount };
})();
