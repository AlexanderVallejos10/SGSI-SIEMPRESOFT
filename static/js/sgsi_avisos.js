(() => {
  "use strict";
  if (window.SGSI && window.SGSI.avisos) return;
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const NS = "http://www.w3.org/2000/svg";
  const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  let chip = null, timer = null, accion = null;
  const REPOSO = 3.5;
  const escudo = { anim: null, linea: "", canvas: null, listo: false, pausa: null, avisar: [] };

  function cargarScript(src) {
    return new Promise((resolve, reject) => {
      if (window.rive) { resolve(); return; }
      const s = document.createElement("script");
      s.src = src; s.async = true; s.onload = resolve; s.onerror = reject;
      document.head.appendChild(s);
    });
  }

  function prepararEscudo() {
    const cfg = document.querySelector("[data-avisos-config]");
    if (!cfg || escudo.anim) return;
    cargarScript(cfg.dataset.riveLib).then(() => {
      const R = window.rive;
      R.RuntimeLoader.setWasmUrl(cfg.dataset.riveWasm);
      escudo.canvas = document.createElement("canvas");
      escudo.canvas.width = 84; escudo.canvas.height = 84;
      escudo.canvas.setAttribute("aria-hidden", "true");
      escudo.anim = new R.Rive({
        src: cfg.dataset.riveEscudo,
        canvas: escudo.canvas,
        autoplay: false,
        layout: new R.Layout({ fit: R.Fit.Contain, alignment: R.Alignment.Center }),
        onLoad: () => {
          const tableros = escudo.anim.contents.artboards || [];
          const tablero = tableros.find((a) => a.name === escudo.anim.activeArtboard) || tableros[0] || {};
          escudo.linea = (tablero.animations || [])[0] || "";
          escudo.listo = !!escudo.linea;
          escudo.avisar.splice(0).forEach((f) => f());
        },
        onLoadError: () => { escudo.avisar.splice(0).forEach((f) => f()); },
      });
    }).catch(() => { escudo.avisar.splice(0).forEach((f) => f()); });
  }

  function esperarEscudo(ms) {
    return new Promise((resolve) => {
      if (escudo.listo || !document.querySelector("[data-avisos-config]")) { resolve(); return; }
      escudo.avisar.push(resolve);
      setTimeout(resolve, ms);
    });
  }

  function trazarEscudo(lugar) {
    if (!escudo.listo || !lugar) return false;
    lugar.appendChild(escudo.canvas);
    clearTimeout(escudo.pausa);
    const { anim, linea } = escudo;
    if (reduce) { anim.pause(); anim.scrub(linea, REPOSO); return true; }
    anim.stop(linea);
    anim.play(linea);
    escudo.pausa = setTimeout(() => { anim.pause(); anim.scrub(linea, REPOSO); }, REPOSO * 1000);
    return true;
  }

  const ICONOS = {
    guardando: '<span class="av-discos" aria-hidden="true"><i></i><i></i><i></i></span>',
    ok: '<svg class="av-ico" viewBox="0 0 16 16" aria-hidden="true"><path pathLength="1" d="M3.2 8.6 6.6 12 12.8 4.6"/></svg>',
    error: '<svg class="av-ico" viewBox="0 0 16 16" aria-hidden="true"><path pathLength="1" d="M8 3.5v5.2"/><path pathLength="1" d="M8 11.6v.4"/></svg>',
    info: '<span class="av-punto" aria-hidden="true"></span>',
  };

  function asegurarChip() {
    if (chip && document.body.contains(chip)) return chip;
    chip = document.createElement("div");
    chip.className = "av-chip";
    chip.setAttribute("role", "status");
    chip.setAttribute("aria-live", "polite");
    chip.hidden = true;
    const destino = window.matchMedia("(max-width: 700px)").matches ? null : document.querySelector(".topbar .top-actions");
    if (destino) destino.prepend(chip); else { chip.classList.add("is-flotante"); document.body.appendChild(chip); }
    chip.addEventListener("click", (ev) => {
      const b = ev.target.closest("[data-av-accion]");
      if (b && accion) { const f = accion; accion = null; f(); return; }
      if (ev.target.closest("[data-av-cerrar]")) ocultar();
    });
    return chip;
  }

  function mostrar(tono, texto, { etiqueta, alHacer, duracion } = {}) {
    const el = asegurarChip();
    clearTimeout(timer);
    accion = alHacer || null;
    el.dataset.tono = tono;
    const conEscudo = tono === "ok" && escudo.listo;
    el.innerHTML = `${conEscudo ? '<span class="av-escudo" data-av-escudo></span>' : ICONOS[tono] || ""}<span class="av-texto">${texto}</span>`
      + (alHacer ? `<button type="button" class="av-accion" data-av-accion>${esc(etiqueta)}</button>` : "")
      + (tono === "error" ? '<button type="button" class="av-cerrar" data-av-cerrar aria-label="Cerrar aviso">×</button>' : "");
    const nuevo = el.hidden;
    el.hidden = false;
    if (conEscudo) trazarEscudo(el.querySelector("[data-av-escudo]"));
    if (!reduce) {
      if (nuevo) el.animate([{ opacity: 0, transform: "translateY(-4px)" }, { opacity: 1, transform: "none" }], { duration: 180, easing: "cubic-bezier(.2,.7,.2,1)" });
      el.querySelectorAll(".av-ico path").forEach((p, i) => {
        p.style.strokeDasharray = "1";
        p.animate([{ strokeDashoffset: 1 }, { strokeDashoffset: 0 }], { duration: 360, delay: i * 120, easing: "cubic-bezier(.2,.7,.2,1)", fill: "both" });
      });
    }
    if (duracion) timer = setTimeout(ocultar, duracion);
  }

  function ocultar() {
    clearTimeout(timer);
    accion = null;
    if (escudo.listo) { clearTimeout(escudo.pausa); escudo.anim.pause(); }
    if (!chip || chip.hidden) return;
    if (reduce) { chip.hidden = true; return; }
    chip.animate([{ opacity: 1 }, { opacity: 0, transform: "translateY(-4px)" }], { duration: 160, easing: "ease-in" }).onfinish = () => { chip.hidden = true; };
  }

  function marcar(el, tono = "ok") {
    if (!el) return;
    if (getComputedStyle(el).position === "static") el.style.position = "relative";
    el.querySelectorAll(":scope > .av-marca").forEach((m) => m.remove());
    const svg = document.createElementNS(NS, "svg");
    svg.setAttribute("viewBox", "0 0 16 16");
    svg.setAttribute("aria-hidden", "true");
    svg.classList.add("av-marca", `is-${tono}`);
    const p = document.createElementNS(NS, "path");
    p.setAttribute("pathLength", "1");
    p.setAttribute("d", tono === "ok" ? "M3.2 8.6 6.6 12 12.8 4.6" : "M4.5 4.5 11.5 11.5 M11.5 4.5 4.5 11.5");
    svg.appendChild(p);
    el.appendChild(svg);
    if (reduce) { setTimeout(() => svg.remove(), 1000); return; }
    p.style.strokeDasharray = "1";
    p.animate([{ strokeDashoffset: 1 }, { strokeDashoffset: 0 }], { duration: 380, easing: "cubic-bezier(.2,.7,.2,1)", fill: "both" });
    el.animate([{ transform: "scale(.94)" }, { transform: "scale(1)" }], { duration: 200, easing: "ease-out" });
    svg.animate([{ opacity: 1 }, { opacity: 1, offset: 0.75 }, { opacity: 0 }], { duration: 1500, fill: "forwards" }).onfinish = () => svg.remove();
  }

  let dialogo = null;
  function confirmar({ titulo = "¿Continuar?", texto = "", accion: etiqueta = "Continuar", peligro = false } = {}) {
    if (!dialogo) {
      dialogo = document.createElement("dialog");
      dialogo.className = "av-dialogo";
      document.body.appendChild(dialogo);
    }
    dialogo.innerHTML = `<form method="dialog"><h2 class="av-d-titulo">${esc(titulo)}</h2>${texto ? `<p class="av-d-texto">${esc(texto)}</p>` : ""}`
      + `<div class="av-d-botones"><button value="no" class="av-d-cancelar">Cancelar</button><button value="si" class="av-d-ok${peligro ? " is-peligro" : ""}">${esc(etiqueta)}</button></div></form>`;
    return new Promise((resolve) => {
      dialogo.addEventListener("close", () => resolve(dialogo.returnValue === "si"), { once: true });
      dialogo.returnValue = "no";
      if (typeof dialogo.showModal === "function") dialogo.showModal(); else resolve(window.confirm(texto || titulo));
      dialogo.querySelector(peligro ? ".av-d-cancelar" : ".av-d-ok")?.focus();
      if (!reduce) dialogo.animate([{ opacity: 0, transform: "translateY(6px) scale(.98)" }, { opacity: 1, transform: "none" }], { duration: 180, easing: "cubic-bezier(.2,.7,.2,1)" });
    });
  }

  const avisos = {
    guardando: (texto = "Guardando…") => mostrar("guardando", esc(texto)),
    guardado: ({ texto = "Guardado", deshacer, el } = {}) => {
      if (el) marcar(el);
      mostrar("ok", esc(texto), deshacer ? { etiqueta: "Deshacer", alHacer: deshacer, duracion: 6000 } : { duracion: 2600 });
    },
    error: (texto = "No se pudo guardar", { reintentar } = {}) => mostrar("error", esc(texto), reintentar ? { etiqueta: "Reintentar", alHacer: reintentar, duracion: 12000 } : { duracion: 12000 }),
    info: (texto, { duracion = 6000 } = {}) => mostrar("info", texto, { duracion }),
    ocultar,
    marcar,
    confirmar,
  };
  window.SGSI = Object.assign(window.SGSI || {}, { avisos });

  document.addEventListener("submit", async (ev) => {
    const form = ev.target;
    const origen = ev.submitter && ev.submitter.dataset.confirmar ? ev.submitter : form;
    if (!origen.dataset || !origen.dataset.confirmar || form.dataset.avConfirmado === "1") return;
    ev.preventDefault();
    const ok = await confirmar({
      titulo: origen.dataset.confirmarTitulo || "¿Continuar?",
      texto: origen.dataset.confirmar,
      accion: origen.dataset.confirmarAccion || "Continuar",
      peligro: "confirmarPeligro" in origen.dataset,
    });
    if (!ok) return;
    form.dataset.avConfirmado = "1";
    if (form.requestSubmit) form.requestSubmit(ev.submitter || undefined); else form.submit();
    setTimeout(() => { delete form.dataset.avConfirmado; }, 0);
  }, true);

  document.addEventListener("DOMContentLoaded", async () => {
    const pila = document.querySelector("[data-mensajes]");
    const items = pila ? Array.from(pila.querySelectorAll("[data-nivel]")) : [];
    if (items.length) {
      pila.hidden = true;
      pila.style.display = "none";
      prepararEscudo();
    } else {
      (window.requestIdleCallback || ((f) => setTimeout(f, 400)))(prepararEscudo);
    }
    if (!items.length) return;
    await esperarEscudo(900);
    const leer = (m) => { const c = m.cloneNode(true); c.querySelectorAll("button").forEach((x) => x.remove()); return c.textContent.trim(); };
    const malo = items.find((m) => /error|warning/.test(m.dataset.nivel));
    if (malo) { avisos.error(leer(malo)); return; }
    const texto = items.map(leer).filter(Boolean).join(" · ");
    mostrar("ok", esc(texto || "Guardado"), { duracion: 4200 });
  });
})();
