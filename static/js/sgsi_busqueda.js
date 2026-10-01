(() => {
  "use strict";
  const raiz = document.querySelector("[data-busqueda]");
  if (!raiz) return;
  const form = raiz.querySelector("[data-bq-form]");
  const input = raiz.querySelector("[data-bq-input]");
  const panel = raiz.querySelector("[data-bq-panel]");
  const abrir = raiz.querySelector("[data-bq-abrir]");
  const URL_SUGERENCIAS = raiz.dataset.sugerencias;
  const CLAVE_RECIENTES = "sgsi-busquedas";
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const VARIANTES = ["aáàäâ", "eéèëê", "iíìïî", "oóòöô", "uúùüû", "nñ", "cç"];
  const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  let pedido = null, espera = null, activo = -1, ultimo = "";

  const clase = (c) => {
    const g = VARIANTES.find((v) => v.includes(c));
    return g ? `[${g}]` : c.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  };
  function resaltar(texto, q) {
    const seguro = esc(texto);
    const terminos = q.toLowerCase().split(/\s+/).filter(Boolean).slice(0, 6);
    if (!terminos.length) return seguro;
    try {
      const inicio = q.trim().length < 3 ? "(?<=^|[\\s\\-_/.,;:(«\"'])" : "";
      const re = new RegExp(`${inicio}(${terminos.map((t) => Array.from(esc(t)).map(clase).join("")).join("|")})`, "gi");
      return seguro.replace(re, "<mark>$1</mark>");
    } catch (e) { return seguro; }
  }

  const recientes = () => { try { return JSON.parse(localStorage.getItem(CLAVE_RECIENTES) || "[]"); } catch (e) { return []; } };
  function recordar(q) {
    q = (q || "").trim();
    if (q.length < 2) return;
    try { localStorage.setItem(CLAVE_RECIENTES, JSON.stringify([q, ...recientes().filter((x) => x.toLowerCase() !== q.toLowerCase())].slice(0, 6))); } catch (e) {}
  }

  const items = () => Array.from(panel.querySelectorAll("[data-bq-item]"));
  function marcarActivo(i) {
    const lista = items();
    activo = lista.length ? (i + lista.length) % lista.length : -1;
    lista.forEach((el, k) => el.setAttribute("aria-selected", k === activo ? "true" : "false"));
    if (activo >= 0) { lista[activo].scrollIntoView({ block: "nearest" }); input.setAttribute("aria-activedescendant", lista[activo].id); }
    else input.removeAttribute("aria-activedescendant");
  }

  function mostrar(html) {
    panel.innerHTML = html;
    const nuevo = panel.hidden;
    panel.hidden = false;
    input.setAttribute("aria-expanded", "true");
    activo = -1;
    if (nuevo && !reduce) panel.animate([{ opacity: 0, transform: "translateY(-4px)" }, { opacity: 1, transform: "none" }], { duration: 140, easing: "cubic-bezier(.2,.7,.2,1)" });
  }
  function cerrar() {
    panel.hidden = true;
    input.setAttribute("aria-expanded", "false");
    raiz.classList.remove("is-abierta");
    activo = -1;
  }

  function pintarRecientes() {
    const lista = recientes();
    if (!lista.length) {
      mostrar('<p class="bq-ayuda">Busque por nombre o código: colaboradores, activos, procesos, riesgos, documentos, archivos Excel o PDF y filas de los registros.</p>');
      return;
    }
    mostrar(`<div class="bq-grupo"><p class="bq-titulo"><svg class="ico" aria-hidden="true"><use href="#i-search"></use></svg>Búsquedas recientes</p>${
      lista.map((q, i) => `<a class="bq-item" id="bq-r-${i}" role="option" data-bq-item href="${form.action}?q=${encodeURIComponent(q)}"><span class="bq-texto">${esc(q)}</span></a>`).join("")}</div>`);
  }

  function pintar(datos, q) {
    const grupos = datos.grupos || [];
    if (!grupos.length) {
      mostrar(`<p class="bq-ayuda">No hay coincidencias para «${esc(q)}».</p>`);
      return;
    }
    let n = 0;
    const html = grupos.map((g) => `<div class="bq-grupo"><p class="bq-titulo"><svg class="ico" aria-hidden="true"><use href="#${esc(g.icono)}"></use></svg>${esc(g.titulo)}</p>${
      g.items.map((it) => `<a class="bq-item" id="bq-i-${n++}" role="option" data-bq-item href="${esc(it.url)}"><span class="bq-texto">${resaltar(it.texto, q)}</span>${it.detalle ? `<span class="bq-detalle">${resaltar(it.detalle, q)}</span>` : ""}${it.codigo ? `<code>${resaltar(it.codigo, q)}</code>` : ""}</a>`).join("")}</div>`).join("");
    mostrar(`${html}<a class="bq-todo" data-bq-item id="bq-todo" role="option" href="${form.action}?q=${encodeURIComponent(q)}">Ver todos los resultados de «${esc(q)}»<kbd>Enter</kbd></a>`);
  }

  async function consultar() {
    const q = input.value.trim();
    if (!q) { ultimo = ""; pintarRecientes(); return; }
    if (q === ultimo && !panel.hidden) return;
    ultimo = q;
    if (pedido) pedido.abort();
    pedido = new AbortController();
    raiz.classList.add("is-buscando");
    try {
      const res = await fetch(`${URL_SUGERENCIAS}?q=${encodeURIComponent(q)}`, { signal: pedido.signal, credentials: "same-origin", headers: { Accept: "application/json" } });
      if (!res.ok) throw new Error(res.status);
      const datos = await res.json();
      if (input.value.trim() === q) pintar(datos, q);
    } catch (e) {
      if (e.name !== "AbortError") mostrar('<p class="bq-ayuda">No se pudo buscar en este momento. Intente de nuevo.</p>');
    } finally {
      raiz.classList.remove("is-buscando");
    }
  }

  input.addEventListener("input", () => { clearTimeout(espera); espera = setTimeout(consultar, 170); });
  input.addEventListener("focus", () => { if (!input.value.trim()) pintarRecientes(); else consultar(); });
  input.addEventListener("keydown", (ev) => {
    if (ev.key === "ArrowDown") { ev.preventDefault(); if (panel.hidden) consultar(); else marcarActivo(activo + 1); }
    else if (ev.key === "ArrowUp") { ev.preventDefault(); marcarActivo(activo - 1); }
    else if (ev.key === "Escape") { if (!panel.hidden) { cerrar(); } else { input.blur(); } }
    else if (ev.key === "Enter" && activo >= 0) {
      ev.preventDefault();
      recordar(input.value);
      window.location.href = items()[activo].href;
    }
  });
  form.addEventListener("submit", (ev) => {
    if (!input.value.trim()) { ev.preventDefault(); return; }
    recordar(input.value);
  });
  panel.addEventListener("click", (ev) => { if (ev.target.closest("[data-bq-item]")) recordar(input.value); });
  panel.addEventListener("mousemove", (ev) => {
    const it = ev.target.closest("[data-bq-item]");
    if (it) marcarActivo(items().indexOf(it));
  });
  document.addEventListener("pointerdown", (ev) => { if (!raiz.contains(ev.target)) cerrar(); });
  abrir?.addEventListener("click", () => { raiz.classList.add("is-abierta"); input.focus(); });

  document.addEventListener("keydown", (ev) => {
    const escribiendo = ev.target.closest && ev.target.closest("input, textarea, select, [contenteditable=true]");
    if ((ev.key === "k" || ev.key === "K") && (ev.ctrlKey || ev.metaKey)) { ev.preventDefault(); raiz.classList.add("is-abierta"); input.focus(); input.select(); }
    else if (ev.key === "/" && !escribiendo && !document.querySelector("dialog[open]")) { ev.preventDefault(); raiz.classList.add("is-abierta"); input.focus(); }
  });
  if (/Mac|iPhone|iPad/.test(navigator.platform || "")) { const k = raiz.querySelector(".bq-atajo"); if (k) k.textContent = "⌘ K"; }
})();
