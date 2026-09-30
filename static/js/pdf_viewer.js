// Visor de PDF propio sobre PDF.js (Mozilla). Primero busca la copia local en static/vendor/pdfjs,
// luego la de cdnjs; si ninguna carga, muestra el visor del navegador sin su barra de herramientas.
(function () {
  "use strict";
  var cfg = document.querySelector("[data-sgsi-loader-config]");
  var LOCAL = cfg && cfg.dataset.pdfjsLocal;
  var LOCAL_WORKER = cfg && cfg.dataset.pdfjsWorkerLocal;
  var CDN = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js";
  var CDN_WORKER = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";
  var libPromise = null;

  function script(src) {
    return new Promise(function (resolve, reject) {
      var el = document.createElement("script");
      el.src = src; el.async = true;
      el.onload = function () { window.pdfjsLib ? resolve(window.pdfjsLib) : reject(new Error("sin pdfjsLib")); };
      el.onerror = reject;
      document.head.appendChild(el);
    });
  }
  function loadLib() {
    if (window.pdfjsLib) return Promise.resolve(window.pdfjsLib);
    if (!libPromise) {
      var worker = LOCAL_WORKER;
      // La copia local es PDF.js 5 (módulo ES); la de respaldo en cdnjs es la 3 (script clásico).
      var local = LOCAL ? import(LOCAL).then(function (m) { return m.getDocument ? m : Promise.reject(new Error("sin getDocument")); }) : Promise.reject();
      libPromise = local
        .catch(function () { worker = CDN_WORKER; return script(CDN); })
        .then(function (lib) { lib.GlobalWorkerOptions.workerSrc = worker; return lib; });
    }
    return libPromise;
  }

  function fallback(viewer, url) {
    var pages = viewer.querySelector("[data-pv-pages]");
    viewer.classList.add("is-fallback");
    pages.innerHTML = "";
    var frame = document.createElement("iframe");
    frame.title = viewer.dataset.title || "Documento";
    frame.src = url + (url.indexOf("#") === -1 ? "#toolbar=0&navpanes=0&view=FitH" : "");
    pages.appendChild(frame);
  }

  function mount(viewer, url) {
    url = url || viewer.dataset.src;
    if (!url) return;
    if (viewer._pv && viewer._pv.url === url) return;
    if (viewer._pv) viewer._pv.destroy();
    var state = { url: url, scale: 1, fitScale: 1, doc: null, pages: [], rendered: new Map(), observer: null, token: 0 };
    viewer._pv = state;
    var pagesBox = viewer.querySelector("[data-pv-pages]");
    var pageInput = viewer.querySelector("[data-pv-page]");
    var count = viewer.querySelector("[data-pv-count]");
    var scaleLabel = viewer.querySelector("[data-pv-scale]");
    viewer.classList.remove("is-fallback", "is-ready");

    state.destroy = function () {
      state.token++;
      if (state.observer) state.observer.disconnect();
      if (state.doc) state.doc.destroy();
    };

    loadLib().then(function (lib) {
      var token = state.token;
      return lib.getDocument({ url: url, withCredentials: true }).promise.then(function (doc) {
        if (token !== state.token) return;
        state.doc = doc;
        count.textContent = doc.numPages;
        return doc.getPage(1).then(function (first) {
          var base = first.getViewport({ scale: 1 });
          state.base = { w: base.width, h: base.height };
          state.fitScale = Math.max(0.3, Math.min(1.35, (pagesBox.clientWidth - 48) / base.width));
          state.scale = state.fitScale;
          build(doc.numPages);
          viewer.classList.add("is-ready");
        });
      });
    }).catch(function () { fallback(viewer, url); });

    function build(n) {
      pagesBox.innerHTML = "";
      state.pages = [];
      state.rendered.clear();
      for (var i = 1; i <= n; i++) {
        var holder = document.createElement("div");
        holder.className = "pv-sheet";
        holder.dataset.page = i;
        holder.style.width = state.base.w * state.scale + "px";
        holder.style.height = state.base.h * state.scale + "px";
        pagesBox.appendChild(holder);
        state.pages.push(holder);
      }
      scaleLabel.textContent = Math.round(state.scale * 100) + "%";
      if (state.observer) state.observer.disconnect();
      state.observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (e) {
          if (e.isIntersecting) draw(Number(e.target.dataset.page));
        });
      }, { root: pagesBox, rootMargin: "400px 0px", threshold: [0, 0.5] });
      state.pages.forEach(function (p) { state.observer.observe(p); });
    }

    function draw(n) {
      var key = n + "@" + state.scale.toFixed(3);
      if (state.rendered.get(n) === key) return;
      state.rendered.set(n, key);
      var token = state.token;
      state.doc.getPage(n).then(function (page) {
        if (token !== state.token) return;
        var ratio = window.devicePixelRatio || 1;
        var vp = page.getViewport({ scale: state.scale });
        var canvas = document.createElement("canvas");
        canvas.width = Math.floor(vp.width * ratio);
        canvas.height = Math.floor(vp.height * ratio);
        canvas.style.width = vp.width + "px";
        canvas.style.height = vp.height + "px";
        var ctx = canvas.getContext("2d");
        page.render({ canvasContext: ctx, viewport: vp, transform: ratio !== 1 ? [ratio, 0, 0, ratio, 0, 0] : null }).promise.then(function () {
          var holder = state.pages[n - 1];
          if (!holder || state.rendered.get(n) !== key) return;
          holder.innerHTML = "";
          holder.appendChild(canvas);
          holder.classList.add("is-drawn");
        });
      });
    }

    function setScale(next) {
      if (!state.doc) return;
      var top = pagesBox.scrollTop / pagesBox.scrollHeight;
      state.scale = Math.max(0.3, Math.min(3, next));
      scaleLabel.textContent = Math.round(state.scale * 100) + "%";
      state.pages.forEach(function (p) {
        p.style.width = state.base.w * state.scale + "px";
        p.style.height = state.base.h * state.scale + "px";
      });
      pagesBox.scrollTop = top * pagesBox.scrollHeight;
      clearTimeout(state.zoomTimer);
      state.zoomTimer = setTimeout(function () {
        state.rendered.clear();
        state.pages.forEach(function (p) {
          var r = p.getBoundingClientRect(); var b = pagesBox.getBoundingClientRect();
          if (r.bottom > b.top - 400 && r.top < b.bottom + 400) draw(Number(p.dataset.page));
        });
      }, 120);
    }
    function goTo(n) {
      if (!state.doc) return;
      n = Math.max(1, Math.min(state.doc.numPages, n));
      pageInput.value = n;
      state.pages[n - 1].scrollIntoView({ behavior: "smooth", block: "start" });
    }

    if (!viewer._pvBound) {
      viewer._pvBound = true;
      viewer.addEventListener("click", function (event) {
        var s = viewer._pv; if (!s) return;
        var b = event.target.closest("button"); if (!b) return;
        if (b.hasAttribute("data-pv-prev")) s.goTo(Number(pageInput.value) - 1);
        else if (b.hasAttribute("data-pv-next")) s.goTo(Number(pageInput.value) + 1);
        else if (b.dataset.pvZoom) s.setScale(s.scale * (Number(b.dataset.pvZoom) > 0 ? 1.2 : 1 / 1.2));
        else if (b.hasAttribute("data-pv-fit")) s.setScale(s.fitScale);
        else if (b.hasAttribute("data-pv-full")) {
          if (document.fullscreenElement) document.exitFullscreen();
          else if (viewer.requestFullscreen) viewer.requestFullscreen();
        }
      });
      pageInput.addEventListener("change", function () { viewer._pv && viewer._pv.goTo(parseInt(pageInput.value, 10) || 1); });
      var scrollTick = null;
      pagesBox.addEventListener("scroll", function () {
        if (scrollTick) return;
        scrollTick = requestAnimationFrame(function () {
          scrollTick = null;
          var s = viewer._pv; if (!s || !s.pages.length || document.activeElement === pageInput) return;
          var b = pagesBox.getBoundingClientRect(); var mark = b.top + b.height / 3;
          var current = s.pages.find(function (p) { var r = p.getBoundingClientRect(); return r.top <= mark && r.bottom >= mark; });
          if (current) pageInput.value = current.dataset.page;
        });
      }, { passive: true });
      pagesBox.addEventListener("wheel", function (event) {
        if (!event.ctrlKey || !viewer._pv) return;
        event.preventDefault();
        viewer._pv.setScale(viewer._pv.scale * Math.exp(-event.deltaY * 0.01));
      }, { passive: false });
    }
    state.setScale = setScale;
    state.goTo = goTo;
  }

  function autoMount() {
    document.querySelectorAll("[data-pdf-viewer][data-src]").forEach(function (v) {
      if (v.dataset.src && !v.hasAttribute("data-pv-manual")) {
        if ("IntersectionObserver" in window) {
          var io = new IntersectionObserver(function (entries) {
            if (entries[0].isIntersecting) { io.disconnect(); mount(v); }
          }, { rootMargin: "200px" });
          io.observe(v);
        } else mount(v);
      }
    });
  }
  window.SGSIPdf = { mount: mount };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", autoMount); else autoMount();
})();
