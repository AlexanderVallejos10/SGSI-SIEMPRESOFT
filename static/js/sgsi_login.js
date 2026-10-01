// Pantalla de ingreso. Con GSAP (static/vendor/gsap, se instala con «instalar_recursos_visuales») hay una
// entrada orquestada con SplitText y DrawSVG, un isotipo de fondo que flota y sigue al puntero, un botón
// magnético, sacudida ante un error y saltos del isotipo mientras se verifica. Sin GSAP, lo mismo con la
// Web Animations API del navegador. Respeta «reducir movimiento». Si algo falla, todo se muestra igual.
(() => {
  "use strict";
  const root = document.documentElement;
  const reveal = () => root.classList.add("motion-ready");
  setTimeout(reveal, 1500); // salvaguarda: nunca queda la página en blanco
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const $ = (s) => document.querySelector(s);
  const $$ = (s) => Array.from(document.querySelectorAll(s));
  const form = $("[data-form]");

  // ---------------------------------------------------------------- utilidades del formulario
  const pass = $("#id_password"), toggle = $("[data-toggle-pass]"), caps = $("[data-caps]");
  toggle?.addEventListener("click", () => {
    const show = pass.type === "password";
    pass.type = show ? "text" : "password";
    toggle.textContent = show ? "Ocultar" : "Mostrar";
    pass.focus();
  });
  pass?.addEventListener("keyup", (e) => caps.classList.toggle("is-on", !!(e.getModifierState && e.getModifierState("CapsLock"))));

  function startRive() {
    const cfg = $("[data-login-config]"), canvas = $("[data-rive]"), R = window.rive;
    if (!R || !canvas || !cfg || !cfg.dataset.riveSrc) return;
    const REPOSO = Number(cfg.dataset.riveReposo || 3.5);
    const inputs = {};
    const set = (name, value) => { const i = inputs[name]; if (i) i.value = value; };
    const fire = (name) => { const i = inputs[name]; if (i && i.fire) i.fire(); };
    let anim = null, linea = "", pausa = null;
    const reposar = () => { if (!anim || !linea) return; anim.pause(); anim.scrub(linea, REPOSO); };
    const trazarUnaVez = () => {
      if (!anim || !linea) return;
      clearTimeout(pausa);
      if (reduce) { reposar(); return; }
      anim.stop(linea);
      anim.play(linea);
      pausa = setTimeout(reposar, REPOSO * 1000);
    };
    try {
      if (cfg.dataset.riveWasm) R.RuntimeLoader.setWasmUrl(cfg.dataset.riveWasm);
      anim = new R.Rive({
        src: cfg.dataset.riveSrc,
        canvas,
        autoplay: false,
        layout: new R.Layout({ fit: R.Fit.Contain, alignment: R.Alignment.CenterLeft }),
        onLoad: () => {
          anim.resizeDrawingSurfaceToCanvas();
          const tablero = (anim.contents.artboards || []).find((a) => a.name === anim.activeArtboard) || (anim.contents.artboards || [])[0] || {};
          const maquinas = (tablero.stateMachines || []).map((m) => m.name);
          $("[data-mark]").classList.add("has-rive");
          if (maquinas.includes("Ingreso") && !reduce) {
            anim.play("Ingreso");
            (anim.stateMachineInputs("Ingreso") || []).forEach((i) => { inputs[i.name] = i; });
            if ($("[data-error]")) fire("error");
            return;
          }
          linea = (tablero.animations || [])[0] || "";
          trazarUnaVez();
        },
      });
    } catch (e) { return; }
    const user = $("#id_username");
    form.addEventListener("focusin", (e) => {
      if (!e.target.matches("input")) return;
      set("enfocado", true);
      set("ocultar", e.target === pass && pass.type === "password");
    });
    form.addEventListener("focusout", () => setTimeout(() => {
      if (!form.contains(document.activeElement) || !document.activeElement.matches("input")) { set("enfocado", false); set("ocultar", false); }
    }, 0));
    user?.addEventListener("input", () => { fire("escribiendo"); set("mirar", Math.min(100, user.value.length * 4)); });
    toggle?.addEventListener("click", () => set("ocultar", pass.type === "password"));
    form.addEventListener("pointermove", (e) => {
      const r = form.getBoundingClientRect();
      set("mirar", Math.round(((e.clientX - r.left) / r.width) * 100));
    });
    form.addEventListener("submit", () => {
      if (inputs.verificando) { set("verificando", true); return; }
      if (!anim || !linea || reduce) return;
      clearTimeout(pausa);
      anim.stop(linea);
      anim.play(linea);
    });
  }
  startRive();

  function playLottie() {
    if ($("[data-mark]")?.classList.contains("has-rive")) return true;
    const box = $("[data-lottie]"), src = $("[data-login-config]")?.dataset.lottieSrc;
    if (reduce || !window.lottie || !box || !src) return false;
    try {
      window.lottie.loadAnimation({ container: box, renderer: "svg", loop: true, autoplay: true, path: src });
      $("[data-mark]").classList.add("has-lottie");
      return true;
    } catch (e) { return false; }
  }

  // ---------------------------------------------------------------- uniones siempre pegadas a los discos
  // Cada curva une dos discos: el inicio y su primer punto de control van con el disco de origen; el final
  // y su segundo punto de control, con el disco de destino. En cada cuadro se toma la posición real de cada
  // disco (movimiento, giro, puntero) y se redibuja la curva: los discos se mueven, pero no se sueltan.
  const SEGMENTS = [
    [0, 1, [47, 37], [51, 29], [51, 23], [51, 22]], // naranja → amarillo
    [1, 2, [73, 22], [80, 23], [86, 28], [88, 34]], // amarillo → verde
    [0, 2, [58, 51], [64, 53], [70, 51], [72, 46]], // naranja → verde
  ];
  function tether(svg) {
    const path = svg && svg.querySelector("path");
    const discs = svg ? Array.from(svg.querySelectorAll("g")) : [];
    if (!path || discs.length < 3 || !svg.createSVGPoint) return;
    const pt = svg.createSVGPoint();
    const at = (m, [x, y]) => { pt.x = x; pt.y = y; const q = pt.matrixTransform(m); return `${q.x.toFixed(2)} ${q.y.toFixed(2)}`; };
    const frame = () => {
      if (!document.hidden) {
        const base = svg.getScreenCTM();
        if (base) {
          const inv = base.inverse();
          const ms = discs.map((d) => inv.multiply(d.getScreenCTM()));
          path.setAttribute("d", SEGMENTS.map(([a, b, p0, c1, c2, p3]) => `M${at(ms[a], p0)} C${at(ms[a], c1)} ${at(ms[b], c2)} ${at(ms[b], p3)}`).join(" "));
        }
      }
      requestAnimationFrame(frame);
    };
    requestAnimationFrame(frame);
  }
  // Trazo que se dibuja con longitud normalizada (100): sirve aunque la curva cambie de largo al moverse
  function prepareStroke(p) { p.setAttribute("pathLength", "100"); p.style.strokeDasharray = "100"; p.style.strokeDashoffset = "100"; }

  function splitWords(el) { // respaldo de SplitText
    const words = el.textContent.trim().split(/\s+/);
    el.innerHTML = words.map((w) => `<span class="word">${w}</span>`).join(" ");
    return Array.from(el.querySelectorAll(".word"));
  }

  if (reduce) { reveal(); form?.addEventListener("submit", () => { $("[data-submit-label]").textContent = "Verificando…"; }); return; }

  try {
    if (window.gsap) runGsap(); else runNative();
  } catch (err) {
    reveal();
  }

  // ================================================================ GSAP
  function runGsap() {
    const gsap = window.gsap;
    const plugins = [window.SplitText, window.DrawSVGPlugin].filter(Boolean);
    if (plugins.length) gsap.registerPlugin(...plugins);
    reveal();

    const words = window.SplitText ? window.SplitText.create(".lg-title", { type: "words", wordsClass: "word" }).words : splitWords($(".lg-title"));
    gsap.set("[data-bg-disc], [data-disc]", { transformOrigin: "50% 100%" });

    const tl = gsap.timeline({ defaults: { ease: "power3.out" } });
    tl.from("[data-stripe]", { scaleX: 0, duration: 0.9, ease: "power2.inOut" })
      .from(".lg-top", { y: -18, autoAlpha: 0, duration: 0.6 }, 0.2)
      .from(words, { yPercent: 115, autoAlpha: 0, rotate: 3, duration: 0.95, stagger: 0.075 }, 0.35)
      .from(".lg-sub", { y: 16, autoAlpha: 0, duration: 0.7 }, 0.95)
      .from(".lg-class", { y: 16, autoAlpha: 0, duration: 0.7 }, 1.1)
      .from("[data-bg-disc]", { y: -90, autoAlpha: 0, duration: 1.3, stagger: 0.16, ease: "bounce.out" }, 0.5)
      .from("[data-disc]", { y: -46, autoAlpha: 0, duration: 1, stagger: 0.13, ease: "back.out(2.4)" }, 0.55)
      .from("[data-in-form]", { y: 20, autoAlpha: 0, duration: 0.65, stagger: 0.07 }, 0.7);
    $$("[data-bg-line], [data-line]").forEach(prepareStroke);
    tl.to("[data-line]", { strokeDashoffset: 0, duration: 0.9, ease: "power2.inOut" }, 1.2)
      .to("[data-bg-line]", { strokeDashoffset: 0, duration: 1.4, ease: "power2.inOut" }, 1.5);
    tether($("[data-bg]"));
    tether($(".lg-discs"));

    // Fondo vivo: cada disco flota a su ritmo y se desplaza con el puntero según su profundidad
    gsap.utils.toArray("[data-bg-disc]").forEach((disc, i) => {
      gsap.to(disc, { y: `+=${7 + i * 4}`, rotation: i % 2 ? 2.5 : -2.5, duration: 3.2 + i * 0.8, ease: "sine.inOut", yoyo: true, repeat: -1, delay: 2 });
    });
    const side = $(".lg-side");
    const movers = gsap.utils.toArray("[data-bg-disc]").map((d) => ({ x: gsap.quickTo(d, "x", { duration: 0.9, ease: "power3" }), depth: Number(d.dataset.depth) || 1 }));
    const bgY = gsap.quickTo("[data-bg]", "y", { duration: 1.1, ease: "power3" });
    side.addEventListener("pointermove", (e) => {
      const r = side.getBoundingClientRect();
      const nx = (e.clientX - r.left) / r.width - 0.5, ny = (e.clientY - r.top) / r.height - 0.5;
      movers.forEach((m) => m.x(nx * 16 * m.depth));
      bgY(ny * 22);
    });
    side.addEventListener("pointerleave", () => { movers.forEach((m) => m.x(0)); bgY(0); });

    // El isotipo del formulario salta en secuencia cada pocos segundos
    const hop = gsap.timeline({ repeat: -1, repeatDelay: 5, delay: 3.2 })
      .to("[data-disc]", { y: -8, duration: 0.24, stagger: 0.12, ease: "power2.out" })
      .to("[data-disc]", { y: 0, duration: 0.5, stagger: 0.12, ease: "bounce.out" }, 0.24);

    // Botón magnético
    const btn = $("[data-magnetic]"), wrap = btn.parentElement;
    const bx = gsap.quickTo(btn, "x", { duration: 0.45, ease: "power3" }), by = gsap.quickTo(btn, "y", { duration: 0.45, ease: "power3" });
    wrap.addEventListener("pointermove", (e) => {
      const r = btn.getBoundingClientRect();
      bx((e.clientX - (r.left + r.width / 2)) * 0.1);
      by((e.clientY - (r.top + r.height / 2)) * 0.3);
    });
    wrap.addEventListener("pointerleave", () => { bx(0); by(0); });
    btn.addEventListener("pointerdown", () => gsap.to(btn, { scale: 0.97, duration: 0.12 }));
    btn.addEventListener("pointerup", () => gsap.to(btn, { scale: 1, duration: 0.3, ease: "back.out(3)" }));

    // Usuario o contraseña incorrectos: el formulario se sacude
    if ($("[data-error]")) tl.add(() => gsap.to(form, { keyframes: { x: [0, -12, 10, -7, 4, 0] }, duration: 0.55, ease: "power1.inOut" }), 1.1);

    // Mientras se verifica: los discos saltan en secuencia y el fondo respira
    form.addEventListener("submit", () => {
      hop.kill();
      $("[data-submit-label]").textContent = "Verificando…";
      if (!playLottie()) gsap.to("[data-disc]", { y: -9, duration: 0.3, stagger: 0.12, yoyo: true, repeat: -1, ease: "power1.inOut" });
      gsap.to("[data-bg-disc]", { scale: 1.05, duration: 0.7, stagger: 0.2, yoyo: true, repeat: -1, ease: "sine.inOut" });
    });
  }

  // ================================================================ Respaldo nativo (Web Animations API)
  function runNative() {
    if (!Element.prototype.animate) { reveal(); return; }
    reveal();
    const ease = "cubic-bezier(.2,.8,.3,1)";
    const fromBelow = (el, delay, dist = 18) => el.animate([{ opacity: 0, transform: `translateY(${dist}px)` }, { opacity: 1, transform: "none" }], { duration: 650, delay, easing: ease, fill: "backwards" });
    $("[data-stripe]").animate([{ transform: "scaleX(0)" }, { transform: "scaleX(1)" }], { duration: 900, easing: "ease-in-out", fill: "backwards" });
    fromBelow($(".lg-top"), 200, -16);
    splitWords($(".lg-title")).forEach((w, i) => w.animate([{ opacity: 0, transform: "translateY(110%) rotate(3deg)" }, { opacity: 1, transform: "none" }], { duration: 900, delay: 350 + i * 75, easing: ease, fill: "backwards" }));
    fromBelow($(".lg-sub"), 950);
    fromBelow($(".lg-class"), 1100);
    $$("[data-in-form]").forEach((el, i) => fromBelow(el, 700 + i * 70, 20));
    $$("[data-bg-disc]").forEach((d, i) => {
      d.animate([{ opacity: 0, transform: "translateY(-90px)" }, { opacity: 1, transform: "translateY(6px)", offset: 0.7 }, { opacity: 1, transform: "none" }], { duration: 1200, delay: 500 + i * 160, easing: ease, fill: "backwards" });
      setTimeout(() => d.animate([{ transform: "none" }, { transform: `translateY(${7 + i * 4}px) rotate(${i % 2 ? 2.5 : -2.5}deg)` }], { duration: 3200 + i * 800, iterations: Infinity, direction: "alternate", easing: "ease-in-out" }), 2000);
    });
    $$("[data-disc]").forEach((d, i) => d.animate([{ opacity: 0, transform: "translateY(-46px)" }, { opacity: 1, transform: "translateY(4px)", offset: 0.75 }, { opacity: 1, transform: "none" }], { duration: 950, delay: 550 + i * 130, easing: ease, fill: "backwards" }));
    $$("[data-bg-line], [data-line]").forEach((p) => {
      prepareStroke(p);
      p.animate([{ strokeDashoffset: 100 }, { strokeDashoffset: 0 }], { duration: 1200, delay: 1300, easing: "ease-in-out", fill: "forwards" });
    });
    tether($("[data-bg]"));
    tether($(".lg-discs"));
    // El fondo sigue al puntero
    const side = $(".lg-side"), bg = $("[data-bg]");
    bg.style.transition = "transform .9s cubic-bezier(.2,.8,.3,1)";
    side.addEventListener("pointermove", (e) => {
      const r = side.getBoundingClientRect();
      bg.style.transform = `translate(${((e.clientX - r.left) / r.width - 0.5) * 24}px, ${((e.clientY - r.top) / r.height - 0.5) * 22}px)`;
    });
    side.addEventListener("pointerleave", () => { bg.style.transform = ""; });
    // Salto periódico del isotipo
    const hopOnce = () => $$("[data-disc]").forEach((d, i) => d.animate([{ transform: "none" }, { transform: "translateY(-8px)", offset: 0.35 }, { transform: "none" }], { duration: 700, delay: i * 120, easing: "cubic-bezier(.4,0,.2,1)" }));
    const hopTimer = setInterval(() => { if (!document.hidden) hopOnce(); }, 6000);
    // Botón magnético
    const btn = $("[data-magnetic]"), wrap = btn.parentElement;
    btn.style.transition = "transform .35s cubic-bezier(.2,.8,.3,1)";
    wrap.addEventListener("pointermove", (e) => {
      const r = btn.getBoundingClientRect();
      btn.style.transform = `translate(${(e.clientX - (r.left + r.width / 2)) * 0.1}px, ${(e.clientY - (r.top + r.height / 2)) * 0.3}px)`;
    });
    wrap.addEventListener("pointerleave", () => { btn.style.transform = ""; });
    if ($("[data-error]")) form.animate([{ transform: "none" }, { transform: "translateX(-12px)" }, { transform: "translateX(10px)" }, { transform: "translateX(-7px)" }, { transform: "translateX(4px)" }, { transform: "none" }], { duration: 550, delay: 1100 });
    form.addEventListener("submit", () => {
      clearInterval(hopTimer);
      $("[data-submit-label]").textContent = "Verificando…";
      if (!playLottie()) $$("[data-disc]").forEach((d, i) => d.animate([{ transform: "none" }, { transform: "translateY(-9px)" }], { duration: 300, delay: i * 120, iterations: Infinity, direction: "alternate", easing: "ease-in-out" }));
    });
  }
})();
