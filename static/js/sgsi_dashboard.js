/* Tablero del SGSI
 * - Datos por API JSON (carga asíncrona con esqueletos) y actualización automática cada 30 s.
 * - Gráficos con D3.js v7 (incluido en static/vendor/d3): barras apiladas, líneas, donas, mapa de calor.
 * - Animaciones con la Web Animations API al entrar cada sección en pantalla; cada sección se dibuja
 *   solo cuando se ve (carga diferida).
 * - Microinteracciones: onda al presionar, tooltips, leyendas que ocultan series, resaltado en matrices.
 * - Personalización: color de acento y densidad, guardados en el navegador.
 */
(() => {
  "use strict";
  const root = document.querySelector("[data-sd]");
  if (!root || !window.d3) return;
  const d3 = window.d3;
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const DUR = reduce ? 0 : 750;
  const POLL_MS = 30000;
  const state = { data: null, version: "", visible: new Set(), drawn: new Set(), timer: null, hidden: {} };
  const csrf = root.querySelector("[data-csrf] input")?.value || "";

  // ------------------------------------------------------------------ utilidades
  const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const num = (v, digits = 0) => (v == null || Number.isNaN(Number(v)) ? "—" : Number(v).toLocaleString("es-PE", { maximumFractionDigits: digits }));
  const pct = (a, b) => (b ? Math.round((100 * a) / b) : 0);
  const $ = (sel, el = root) => el.querySelector(sel);
  const width = (el) => Math.max(260, el.getBoundingClientRect().width);

  // ------------------------------------------------------------------ preferencias
  // El acento y la densidad se eligen en la barra superior (sd_ui.js); al cambiar la densidad se redibuja.
  document.addEventListener("sd:density", () => redrawAll());
  root.addEventListener("click", (ev) => { if (ev.target.closest("[data-refresh]")) load({ force: true }); });

  // ------------------------------------------------------------------ microinteracciones
  root.addEventListener("pointerdown", (ev) => {
    const btn = ev.target.closest(".sd-press");
    if (!btn || reduce) return;
    const r = btn.getBoundingClientRect();
    const size = Math.max(r.width, r.height);
    const dot = document.createElement("span");
    dot.className = "sd-ripple";
    dot.style.cssText = `width:${size}px;height:${size}px;left:${ev.clientX - r.left - size / 2}px;top:${ev.clientY - r.top - size / 2}px`;
    btn.appendChild(dot);
    setTimeout(() => dot.remove(), 600);
  });

  const tip = $("[data-tip]");
  const showTip = (html, ev) => {
    tip.innerHTML = html; tip.hidden = false;
    const pad = 14, w = tip.offsetWidth, h = tip.offsetHeight;
    let x = ev.clientX + pad, y = ev.clientY + pad;
    if (x + w > window.innerWidth - 8) x = ev.clientX - w - pad;
    if (y + h > window.innerHeight - 8) y = ev.clientY - h - pad;
    tip.style.left = `${x}px`; tip.style.top = `${y}px`;
  };
  const hideTip = () => { tip.hidden = true; };

  const avisos = () => window.SGSI && window.SGSI.avisos;
  const toast = (html, tone = "info") => {
    const av = avisos();
    if (!av) return;
    if (tone === "bad") av.error(html.replace(/<[^>]+>/g, "")); else av.info(html);
  };

  // Aparición escalonada (Web Animations API)
  const reveal = (el) => { // un único momento: los gráficos se dibujan al cargar; las tarjetas no se animan
    return;
    // eslint-disable-next-line no-unreachable
    if (reduce) return;
    const kids = el.matches(".sd-metrics, .sd-oesi, .sd-kpis") ? [...el.children] : [el];
    kids.forEach((k, i) => k.animate(
      [{ opacity: 0, transform: "translateY(14px)" }, { opacity: 1, transform: "none" }],
      { duration: 520, delay: i * 55, easing: "cubic-bezier(.2,.7,.2,1)", fill: "backwards" },
    ));
  };

  // Pestañas con indicador deslizante y sección activa
  const tabs = [...root.querySelectorAll("[data-tabs] a")];
  const ink = $("[data-tabs-ink]");
  const moveInk = (a) => {
    tabs.forEach((t) => t.classList.toggle("is-on", t === a));
    if (a && ink) { ink.style.width = `${a.offsetWidth}px`; ink.style.transform = `translateX(${a.offsetLeft}px)`; }
  };
  moveInk(tabs[0]);
  const spy = new IntersectionObserver((entries) => entries.forEach((e) => {
    if (e.isIntersecting) moveInk(tabs.find((a) => a.getAttribute("href") === `#${e.target.id}`));
  }), { rootMargin: "-35% 0px -60% 0px" });
  tabs.forEach((a) => { const s = document.querySelector(a.getAttribute("href")); if (s) spy.observe(s); });

  // ------------------------------------------------------------------ tiempo real
  const live = $("[data-live]");
  const liveText = $("[data-live-text]");
  let lastOk = null;
  const setLive = (mode, text) => {
    live.classList.toggle("is-on", mode === "on"); live.classList.toggle("is-busy", mode === "busy");
    if (text) liveText.textContent = text;
  };
  setInterval(() => {
    if (!lastOk) return;
    const s = Math.round((Date.now() - lastOk) / 1000);
    liveText.textContent = s < 5 ? "Actualizado recién" : `Actualizado hace ${s < 60 ? `${s} s` : `${Math.round(s / 60)} min`}`;
  }, 5000);

  const diffMessages = (old, now) => {
    if (!old) return [];
    const msgs = [];
    const o = old.overview || {}, n = now.overview || {};
    const cmp = (a, b, label, tone) => {
      if (a == null || b == null || a === b) return;
      msgs.push([`<b>${label}</b> pasó de ${num(a)} a ${num(b)}.`, tone]);
    };
    cmp(o.incidents?.total, n.incidents?.total, "Incidentes", "bad");
    cmp(o.corrective?.done, n.corrective?.done, "Medidas implementadas", "ok");
    cmp(o.audits?.open, n.audits?.open, "Hallazgos abiertos", "warn");
    cmp(o.risks?.total, n.risks?.total, "Riesgos", "info");
    cmp(old.summary?.sgsi?.[0], now.summary?.sgsi?.[0], "Indicadores que cumplen", "ok");
    cmp(old.summary?.oesi?.[0], now.summary?.oesi?.[0], "OESI en meta", "ok");
    return msgs;
  };

  async function load({ force = false, quiet = false } = {}) {
    const refreshBtn = $("[data-refresh]");
    refreshBtn?.classList.add("is-spinning");
    setLive("busy", "Consultando…");
    try {
      const url = new URL(root.dataset.api, window.location.origin);
      if (state.version && !force) url.searchParams.set("v", state.version);
      if (force) url.searchParams.set("refresh", "1");
      const res = await fetch(url, { credentials: "same-origin", headers: { Accept: "application/json" } });
      if (!res.ok) throw new Error(res.status);
      const data = await res.json();
      lastOk = Date.now();
      setLive("on", "Actualizado recién");
      if (data.unchanged) return;
      const msgs = diffMessages(state.data, data);
      state.data = data; state.version = data.version;
      paintLead();
      redrawAll();
      if (msgs.length && !quiet) toast(msgs.length === 1 ? msgs[0][0] : `${msgs[0][0]} y ${msgs.length - 1} cambio${msgs.length > 2 ? "s" : ""} más.`, msgs[0][1]);
    } catch (e) {
      setLive("off", "Sin conexión con el servidor");
    } finally {
      refreshBtn?.classList.remove("is-spinning");
    }
  }
  const schedule = () => { clearInterval(state.timer); state.timer = setInterval(() => { if (!document.hidden) load(); }, POLL_MS); };
  document.addEventListener("visibilitychange", () => { if (!document.hidden && lastOk && Date.now() - lastOk > POLL_MS) load(); });

  // ------------------------------------------------------------------ carga diferida por sección
  const renderers = {};
  const io = new IntersectionObserver((entries) => entries.forEach((e) => {
    if (!e.isIntersecting || state.drawn.has(e.target)) return; // se dibuja una sola vez; luego solo al cambiar los datos
    state.visible.add(e.target);
    draw(e.target);
  }), { rootMargin: "120px 0px" });
  root.querySelectorAll("[data-render]").forEach((el) => io.observe(el));

  function draw(el) {
    if (!state.data) return;
    const fn = renderers[el.dataset.render];
    if (!fn) return;
    const first = !state.drawn.has(el);
    fn(el, state.data, first);
    // Accesibilidad: cada gráfico se anuncia con el título de su tarjeta; el detalle está en la leyenda y los textos
    const title = el.querySelector("h3, .sd-card-head b, .sd-card-head span")?.textContent?.trim();
    el.querySelectorAll("svg.sd-chart").forEach((svg) => { svg.setAttribute("role", "img"); if (title) svg.setAttribute("aria-label", title); });
    if (first) { state.drawn.add(el); reveal(el); }
  }
  function redrawAll() { state.visible.forEach(draw); }
  let resizeTimer, lastWidth = window.innerWidth;
  window.addEventListener("resize", () => { // solo si cambia el ancho (en móviles el alto cambia al desplazarse)
    if (window.innerWidth === lastWidth) return;
    lastWidth = window.innerWidth;
    clearTimeout(resizeTimer); resizeTimer = setTimeout(redrawAll, 180);
  });

  const cardHead = (title, link, linkText = "Ver detalle") => `<div class="sd-card-head"><h3>${esc(title)}</h3>${link ? `<a href="${esc(link)}">${esc(linkText)}</a>` : ""}</div>`;
  const empty = (el, title, text) => { el.innerHTML = `${cardHead(title)}<p class="sd-card-note">${esc(text)}</p>`; };

  function paintLead() {
    const d = state.data, lead = $("[data-lead]");
    if (!d.dataset) { lead.innerHTML = "Todavía no se cargó el Excel del tablero. Ejecute <b>cargar_todo_siempresoft --paso dashboard</b> o súbalo con «Subir nueva versión»."; return; }
    const warn = (d.warnings || []).length;
    lead.innerHTML = `Mediciones y objetivos de seguridad de <b>${esc(d.dataset.name)}</b>${d.dataset.version ? ` (versión ${esc(d.dataset.version)})` : ""}, cruzados con el estado real de riesgos, incidentes, auditorías, activos y documentos.`
      + (warn ? ` <span class="sd-state t-warn" style="display:inline-flex;margin:0 0 0 6px" title="${esc(d.warnings.map((w) => `${w.title}: ${w.detail}`).join("; "))}">${warn} alerta${warn > 1 ? "s" : ""} de calidad del dato</span>` : "");
  }

  // ------------------------------------------------------------------ micro gráficos de los KPI
  function segments(svg, items) { // un segmento por indicador: verde si cumple, rojo si no
    const w = width(svg.node()), h = 10, gap = 3, n = items.length || 1, sw = (w - gap * (n - 1)) / n;
    svg.attr("viewBox", `0 0 ${w} 32`).selectAll("rect").data(items).join("rect")
      .attr("y", 16).attr("height", 6).attr("rx", 1).attr("x", (_, i) => i * (sw + gap)).attr("width", 0)
      .attr("class", (d) => `t-${d.ok ? "ok" : "bad"}`).style("fill", "var(--c)")
      .on("mousemove", (ev, d) => showTip(`<b>${esc(d.label)}</b><br>${d.ok ? "Cumple" : "No cumple"}`, ev)).on("mouseleave", hideTip)
      .transition().duration(DUR).delay((_, i) => i * 60).attr("width", sw);
  }
  function spark(svg, values, labels, tone) {
    const w = width(svg.node()), h = 32;
    if (!values.length) return;
    const x = d3.scalePoint().domain(d3.range(values.length)).range([2, w - 2]);
    const y = d3.scaleLinear().domain([0, d3.max(values) || 1]).nice().range([h - 3, 4]);
    svg.attr("viewBox", `0 0 ${w} ${h}`).attr("class", `t-${tone}`);
    const line = d3.line().x((_, i) => x(i)).y((v) => y(v)).curve(d3.curveMonotoneX);
    const area = d3.area().x((_, i) => x(i)).y0(h).y1((v) => y(v)).curve(d3.curveMonotoneX);
    svg.selectAll("path.spark-area").data([values]).join("path").attr("class", "spark-area").attr("d", area);
    const path = svg.selectAll("path.spark-line").data([values]).join("path").attr("class", "spark-line").attr("d", line);
    if (!reduce) { const L = path.node().getTotalLength(); path.attr("stroke-dasharray", `${L} ${L}`).attr("stroke-dashoffset", L).transition().duration(DUR * 1.4).attr("stroke-dashoffset", 0); }
    const last = values.length - 1;
    svg.selectAll("circle").data(values.map((v, i) => [v, i])).join("circle").attr("class", "spark-dot")
      .attr("r", (d) => (d[1] === last ? 3 : 0)).attr("cx", (d) => x(d[1])).attr("cy", (d) => y(d[0]));
    svg.on("mousemove", (ev) => {
      const [mx] = d3.pointer(ev); const i = d3.minIndex(values.map((_, k) => Math.abs(x(k) - mx)));
      svg.selectAll("circle").attr("r", (d) => (d[1] === i ? 3.5 : d[1] === last ? 3 : 0));
      showTip(`<b>${esc(labels[i])}</b>: ${num(values[i])}`, ev);
    }).on("mouseleave", () => { hideTip(); svg.selectAll("circle").attr("r", (d) => (d[1] === last ? 3 : 0)); });
  }
  function levels(svg, lv) {
    const w = width(svg.node()), total = d3.sum(lv, (d) => d.count) || 1;
    let x0 = 0;
    const data = lv.map((d) => { const r = { ...d, x: x0, w: (w * d.count) / total }; x0 += r.w; return r; });
    svg.attr("viewBox", `0 0 ${w} 32`).selectAll("rect").data(data).join("rect")
      .attr("y", 16).attr("height", 6).attr("class", (d) => `t-${d.tone}`).style("fill", "var(--c)")
      .attr("x", (d) => d.x).attr("width", 0)
      .on("mousemove", (ev, d) => showTip(`<b>${esc(d.name)}</b>: ${d.count}`, ev)).on("mouseleave", hideTip)
      .transition().duration(DUR).attr("width", (d) => Math.max(0, d.w - 2));
  }
  function progress(svg, value, tone) {
    const w = width(svg.node());
    svg.attr("viewBox", `0 0 ${w} 32`).attr("class", `t-${tone}`);
    svg.selectAll("rect.arc-track").data([0]).join("rect").attr("class", "arc-track").attr("y", 16).attr("height", 6).attr("rx", 1).attr("width", w);
    svg.selectAll("rect.arc-bar").data([value]).join("rect").attr("class", "arc-bar").attr("y", 16).attr("height", 6).attr("rx", 1)
      .attr("width", 0).transition().duration(DUR).attr("width", (v) => (w * Math.min(100, v)) / 100);
  }

  renderers.kpis = (el, d) => {
    const ov = d.overview || {}, s = d.summary || {};
    const tiles = [];
    if (d.dataset) {
      tiles.push({ key: "sgsi", label: "Indicadores del SGSI", value: `${s.sgsi[0]}<span>/ ${s.sgsi[1]}</span>`, note: "cumplen su meta", href: "#indicadores",
        chart: (svg) => segments(svg, d.sgsi.map((m) => ({ ok: m.ok, label: `M${m.id}. ${m.description}` }))) });
      tiles.push({ key: "oesi", label: "Objetivos de seguridad", value: `${s.oesi[0]}<span>/ ${s.oesi[1]}</span>`, note: "OESI en meta", href: "#objetivos",
        chart: (svg) => segments(svg, d.oesi.map((m) => ({ ok: m.ok, label: `OESI${m.id}. ${m.description}` }))) });
    }
    if (ov.risks) tiles.push({ key: "risks", label: "Riesgos", value: num(ov.risks.total), note: `${ov.risks.high} en nivel alto o muy alto`, href: d.links.risks, chart: (svg) => levels(svg, ov.risks.levels) });
    if (ov.incidents) tiles.push({ key: "inc", label: "Incidentes", value: num(ov.incidents.total), note: ov.incidents.last_year ? `${ov.incidents.last_count} en ${ov.incidents.last_year}` : "", href: d.links.incidents,
      chart: (svg) => spark(svg, ov.incidents.years.map((_, i) => d3.sum(ov.incidents.series, (x) => x.values[i])), ov.incidents.years.map(String), "info") });
    if (ov.corrective) tiles.push({ key: "cor", label: "Medidas implementadas", value: `${ov.corrective.pct}<span>%</span>`, note: `${ov.corrective.pending} pendientes`, href: d.links.corrective,
      chart: (svg) => spark(svg, ov.corrective.years.map((_, i) => pct(ov.corrective.series[0].values[i], ov.corrective.series[0].values[i] + ov.corrective.series[1].values[i])), ov.corrective.years.map((y) => `${y} (% implementadas)`), "ok") });
    if (ov.documents) tiles.push({ key: "doc", label: "Documentos del Manual", value: `${ov.documents.pct}<span>%</span>`, note: `${ov.documents.found} de ${ov.documents.total} en el sistema`, href: "#estado",
      chart: (svg) => progress(svg, ov.documents.pct, ov.documents.pct >= 90 ? "ok" : "warn") });
    el.innerHTML = tiles.map((t) => `<a class="sd-kpi" href="${esc(t.href)}" data-k="${t.key}"><span class="sd-kpi-label">${esc(t.label)}</span>
      <span class="sd-kpi-value"><b class="num">${t.value}</b></span><small>${esc(t.note)}</small><svg aria-hidden="true"></svg></a>`).join("");
    tiles.forEach((t) => t.chart(d3.select(el.querySelector(`[data-k="${t.key}"] svg`))));
  };

  // ------------------------------------------------------------------ indicadores y OESI (gráfico de viñeta)
  function bullet(svg, b, ok) { // barra fina de extremos rectos; la meta es una línea delgada que la cruza
    const w = width(svg.node()), h = 22, y = 8, bh = 6;
    svg.attr("viewBox", `0 0 ${w} ${h}`).attr("class", `sd-bullet t-${ok ? "ok" : "bad"}`);
    if (!b) { svg.selectAll("*").remove(); return; }
    const x = d3.scaleLinear().domain([0, 100]).range([0, w]);
    svg.selectAll("rect.b-track").data([0]).join("rect").attr("class", "b-track").attr("y", y).attr("height", bh).attr("rx", 1).attr("width", w);
    svg.selectAll("rect.b-bar").data([b.value_pct]).join("rect").attr("class", "b-bar").attr("y", y).attr("height", bh).attr("rx", 1)
      .transition().duration(DUR).attr("width", (v) => Math.max(2, x(v)));
    svg.selectAll("rect.b-target").data([b.target_pct]).join("rect").attr("class", "b-target").attr("y", y - 5).attr("height", bh + 10).attr("width", 2).attr("rx", 0)
      .transition().duration(DUR).attr("x", (v) => Math.min(w - 2, Math.max(0, x(v) - 1)));
  }
  const direction = (b) => (!b ? "" : b.direction === "up" ? "Mejor mientras más alto" : b.direction === "down" ? "Mejor mientras más bajo" : "Debe igualar la meta");

  renderers.metrics = (el, d, first) => {
    if (!d.dataset) { el.innerHTML = '<p class="sd-card-note">Sin tablero cargado.</p>'; return; }
    if (first || el.children.length !== d.sgsi.length || el.querySelector(".is-skeleton")) {
      el.innerHTML = d.sgsi.map((m) => `<article class="sd-card sd-metric t-${m.ok ? "ok" : "bad"}" data-id="${m.id}">
        <div class="sd-metric-top"><span class="code">M${m.id}</span>${m.pdca ? `<span class="sd-tag" title="Ciclo PDCA">${esc(m.pdca)}</span>` : ""}<span class="sd-state">${m.ok ? "Cumple" : "No cumple"}</span></div>
        <h3>${esc(m.description)}</h3>
        <div class="sd-metric-value"><b class="num">${esc(m.display)}</b><span>meta ${esc(m.indicator)}</span></div>
        <svg class="sd-bullet" aria-label="Valor frente a la meta"></svg>
        <div class="sd-meta"><span>${esc(direction(m.bullet))}</span><span><b>${esc(m.responsible || "—")}</b></span><span>${esc(m.period || "")}</span></div>
        ${m.plan ? `<details class="sd-plan"><summary>Plan de acción</summary><p>${esc(m.plan)}</p></details>` : ""}
        ${m.edit_url ? `<a class="sd-edit" href="${esc(m.edit_url)}">Editar</a>` : ""}</article>`).join("");
    }
    d.sgsi.forEach((m) => bullet(d3.select(el.querySelector(`[data-id="${m.id}"] svg`)), m.bullet, m.ok));
  };

  let oesiFilter = "all";
  function applyOesiFilter(el, animate = true) { // FLIP: las filas se deslizan a su nueva posición
    const rows = [...el.children];
    const before = new Map(rows.map((r) => [r, r.getBoundingClientRect().top]));
    rows.forEach((r) => { r.hidden = oesiFilter !== "all" && r.dataset.ok !== oesiFilter; });
    if (!animate || reduce) return;
    rows.filter((r) => !r.hidden).forEach((r) => {
      const dy = before.get(r) - r.getBoundingClientRect().top;
      if (dy) r.animate([{ transform: `translateY(${dy}px)` }, { transform: "none" }], { duration: 320, easing: "cubic-bezier(.2,.7,.2,1)" });
      else r.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 260 });
    });
  }
  renderers.oesi = (el, d, first) => {
    if (!d.dataset) { el.innerHTML = '<p class="sd-card-note">Sin tablero cargado.</p>'; return; }
    if (first || el.querySelector(".is-skeleton") || el.children.length !== d.oesi.length) {
      el.innerHTML = d.oesi.map((m) => `<div class="sd-oesi-row t-${m.ok ? "ok" : "bad"}" data-id="${m.id}" data-ok="${m.ok ? "ok" : "bad"}">
        <span class="code">OESI${m.id}</span>
        <div><b class="t">${esc(m.description)}</b><small>${esc(m.responsible || "")}${m.period ? `, ${esc(m.period)}` : ""}</small></div>
        <div><svg class="sd-bullet"></svg><small><b class="num">${esc(m.display)}${m.bullet?.unit || ""}</b>, meta ${esc(m.indicator)}</small></div>
        <span class="sd-state">${m.ok ? "Cumple" : "No cumple"}</span></div>`).join("");
    }
    d.oesi.forEach((m) => bullet(d3.select(el.querySelector(`[data-id="${m.id}"] svg`)), m.bullet, m.ok));
    applyOesiFilter(el, false);
  };
  root.querySelector("[data-oesi-filter]")?.addEventListener("click", (ev) => {
    const b = ev.target.closest("button[data-f]"); if (!b) return;
    oesiFilter = b.dataset.f;
    b.parentElement.querySelectorAll("button").forEach((x) => x.classList.toggle("is-on", x === b));
    applyOesiFilter($('[data-render="oesi"]'));
  });

  // ------------------------------------------------------------------ mapa de calor de riesgos
  renderers.heat = (el, d) => {
    const r = d.overview?.risks;
    if (!r) return empty(el, "Mapa de calor de riesgos", "Sin datos de riesgos.");
    el.innerHTML = `${cardHead("Mapa de calor de riesgos", d.links.risks, "Ver matriz")}<div class="sd-heat-wrap"><svg class="sd-chart sd-heat"></svg><ul class="sd-legend is-col"></ul></div>`;
    const cell = 46, pad = 30, W = pad + cell * 5, H = cell * 4 + 34;
    const svg = d3.select(el.querySelector("svg")).attr("viewBox", `0 0 ${W} ${H}`).attr("width", W).attr("height", H);
    const cells = r.grid.flatMap((row, ri) => row.cells.map((c) => ({ ...c, p: row.p, ri })));
    const g = svg.selectAll("g.c").data(cells).join("g").attr("class", "c").attr("transform", (c) => `translate(${pad + (c.i - 1) * cell},${c.ri * cell})`);
    g.append("rect").attr("class", (c) => `cell t-${c.tone}${c.count ? " has" : ""}`).attr("width", cell).attr("height", cell).attr("rx", 7)
      .style("opacity", 0).transition().duration(DUR).delay((c) => (c.ri + c.i) * 35).style("opacity", 1);
    g.filter((c) => c.count).append("text").attr("class", "count").attr("x", cell / 2).attr("y", cell / 2 + 5).text((c) => c.count);
    g.on("mousemove", (ev, c) => {
      svg.selectAll("rect.cell").classed("is-dim", (o) => o !== c);
      showTip(`<b>${esc(c.level)}</b><br>Probabilidad ${c.p}, consecuencia ${c.i}<br>${c.count} riesgo${c.count === 1 ? "" : "s"}`, ev);
    }).on("mouseleave", () => { svg.selectAll("rect.cell").classed("is-dim", false); hideTip(); })
      .on("click", () => { window.location.href = d.links.risks; });
    svg.selectAll("text.py").data([4, 3, 2, 1]).join("text").attr("class", "lab py").attr("x", pad - 12).attr("y", (_, i) => i * cell + cell / 2 + 4).text((v) => v);
    svg.selectAll("text.px").data([1, 2, 3, 4, 5]).join("text").attr("class", "lab px").attr("x", (v) => pad + (v - 1) * cell + cell / 2).attr("y", cell * 4 + 14).text((v) => v);
    svg.append("text").attr("class", "lab").attr("x", pad + (cell * 5) / 2).attr("y", H - 2).text("Consecuencia");
    el.querySelector("ul").innerHTML = r.levels.map((l) => `<li class="t-${l.tone}"><span style="display:inline-flex;align-items:center;gap:7px"><i></i>${esc(l.name)}</span><b>${l.count}</b></li>`).join("");
  };

  // ------------------------------------------------------------------ barras apiladas con leyenda interactiva
  function stacked(el, title, link, years, series, key) {
    el.innerHTML = `${cardHead(title, link, "Ver registro")}<svg class="sd-chart"></svg><ul class="sd-legend"></ul>`;
    const hidden = state.hidden[key] || (state.hidden[key] = new Set());
    const W = width(el) - 2, H = 220, m = { t: 18, r: 6, b: 24, l: 30 };
    const svg = d3.select(el.querySelector("svg")).attr("viewBox", `0 0 ${W} ${H}`);
    const x = d3.scaleBand().domain(years).range([m.l, W - m.r]).padding(0.34);
    const y = d3.scaleLinear().range([H - m.b, m.t]);
    const gGrid = svg.append("g").attr("class", "grid").attr("transform", `translate(${m.l},0)`);
    const gX = svg.append("g").attr("class", "axis").attr("transform", `translate(0,${H - m.b})`);
    const gBars = svg.append("g"), gTot = svg.append("g");
    const legend = d3.select(el.querySelector("ul"));

    const update = () => {
      const keys = series.filter((s) => !hidden.has(s.name));
      const rows = years.map((yr, i) => Object.fromEntries([["year", yr], ...keys.map((s) => [s.name, s.values[i]])]));
      const stack = d3.stack().keys(keys.map((s) => s.name))(rows);
      y.domain([0, d3.max(rows, (r) => d3.sum(keys, (s) => r[s.name])) || 1]).nice();
      gGrid.transition().duration(DUR).call(d3.axisLeft(y).ticks(4).tickSize(-(W - m.l - m.r)).tickFormat(d3.format("d")));
      gX.call(d3.axisBottom(x).tickSize(0).tickPadding(8)).select(".domain").remove();
      const layer = gBars.selectAll("g.layer").data(stack, (s) => s.key).join(
        (enter) => enter.append("g"), (u) => u, (exit) => exit.transition().duration(DUR / 2).style("opacity", 0).remove());
      layer.attr("class", (s) => `layer t-${series.find((q) => q.name === s.key).tone}`);
      layer.selectAll("rect").data((s) => s.map((v) => ({ v, key: s.key })), (r) => r.v.data.year).join(
        (enter) => enter.append("rect").attr("class", "bar").attr("x", (r) => x(r.v.data.year)).attr("width", x.bandwidth()).attr("rx", 1)
          .attr("y", y(0)).attr("height", 0),
      ).transition().duration(DUR).delay((_, i) => i * 40)
        .attr("x", (r) => x(r.v.data.year)).attr("width", x.bandwidth())
        .attr("y", (r) => y(r.v[1])).attr("height", (r) => Math.max(0, y(r.v[0]) - y(r.v[1]) - (r.v[1] - r.v[0] ? 1 : 0)));
      gTot.selectAll("text").data(rows, (r) => r.year).join("text").attr("class", "total").attr("text-anchor", "middle")
        .attr("x", (r) => x(r.year) + x.bandwidth() / 2).transition().duration(DUR)
        .attr("y", (r) => y(d3.sum(keys, (s) => r[s.name])) - 6).text((r) => d3.sum(keys, (s) => r[s.name]) || "");
      svg.selectAll("rect.bar").on("mousemove", (ev, r) => {
        const yr = r.v.data.year;
        svg.selectAll("rect.bar").classed("is-dim", (o) => o.v.data.year !== yr);
        showTip(`<b>${yr}</b><br>${series.map((s) => `${esc(s.name)}: <b>${s.values[years.indexOf(yr)]}</b>`).join("<br>")}`, ev);
      }).on("mouseleave", () => { svg.selectAll("rect.bar").classed("is-dim", false); hideTip(); });
      legend.selectAll("li").data(series).join("li").attr("class", (s) => `t-${s.tone}${hidden.has(s.name) ? " is-off" : ""}`)
        .html((s) => `<i></i>${esc(s.name)} <b>${d3.sum(s.values)}</b>`).attr("title", "Clic para ocultar o mostrar")
        .on("click", (_, s) => { if (hidden.has(s.name)) hidden.delete(s.name); else hidden.add(s.name); if (hidden.size === series.length) hidden.delete(s.name); update(); });
    };
    update();
  }
  renderers.incidents = (el, d) => {
    const inc = d.overview?.incidents;
    if (!inc || !inc.years.length) return empty(el, "Incidentes por año", "Sin incidentes registrados.");
    stacked(el, "Incidentes por año y severidad", d.links.incidents, inc.years.map(String), inc.series, "inc");
  };

  // ------------------------------------------------------------------ medidas: líneas con cruz de lectura
  renderers.corrective = (el, d) => {
    const c = d.overview?.corrective;
    if (!c || !c.years.length) return empty(el, "Medidas correctivas", "Sin medidas registradas.");
    el.innerHTML = `${cardHead("Medidas correctivas y de mejora", d.links.corrective, "Ver registro")}<svg class="sd-chart"></svg><ul class="sd-legend"></ul>`;
    const W = width(el) - 2, H = 220, m = { t: 14, r: 10, b: 24, l: 30 };
    const years = c.years.map(String);
    const svg = d3.select(el.querySelector("svg")).attr("viewBox", `0 0 ${W} ${H}`);
    const x = d3.scalePoint().domain(years).range([m.l + 8, W - m.r - 8]);
    const y = d3.scaleLinear().domain([0, d3.max(c.series.flatMap((s) => s.values)) || 1]).nice().range([H - m.b, m.t]);
    svg.append("g").attr("class", "grid").attr("transform", `translate(${m.l},0)`).call(d3.axisLeft(y).ticks(4).tickSize(-(W - m.l - m.r)).tickFormat(d3.format("d")));
    svg.append("g").attr("class", "axis").attr("transform", `translate(0,${H - m.b})`).call(d3.axisBottom(x).tickSize(0).tickPadding(8)).select(".domain").remove();
    c.series.forEach((s, k) => {
      const g = svg.append("g").attr("class", `t-${s.tone}`);
      if (k === 0) g.append("path").attr("class", "area").attr("d", d3.area().x((_, i) => x(years[i])).y0(H - m.b).y1((v) => y(v)).curve(d3.curveMonotoneX)(s.values));
      const path = g.append("path").attr("class", "line").attr("d", d3.line().x((_, i) => x(years[i])).y((v) => y(v)).curve(d3.curveMonotoneX)(s.values));
      if (!reduce) { const L = path.node().getTotalLength(); path.attr("stroke-dasharray", `${L} ${L}`).attr("stroke-dashoffset", L).transition().duration(DUR * 1.5).delay(k * 200).attr("stroke-dashoffset", 0); }
      g.selectAll("circle").data(s.values).join("circle").attr("class", "dot").attr("r", reduce ? 3.5 : 0).attr("cx", (_, i) => x(years[i])).attr("cy", (v) => y(v))
        .transition().delay((_, i) => DUR + i * 50).duration(250).attr("r", 3.5);
    });
    const cross = svg.append("line").attr("class", "cross").attr("y1", m.t).attr("y2", H - m.b).style("opacity", 0);
    svg.append("rect").attr("x", m.l).attr("y", m.t).attr("width", W - m.l - m.r).attr("height", H - m.t - m.b).attr("fill", "transparent")
      .on("mousemove", (ev) => {
        const [mx] = d3.pointer(ev); const i = d3.minIndex(years.map((yr) => Math.abs(x(yr) - mx)));
        cross.attr("x1", x(years[i])).attr("x2", x(years[i])).style("opacity", 1);
        const tot = c.series[0].values[i] + c.series[1].values[i];
        showTip(`<b>${years[i]}</b><br>${c.series.map((s) => `${esc(s.name)}: <b>${s.values[i]}</b>`).join("<br>")}<br>${pct(c.series[0].values[i], tot)} % implementadas`, ev);
      }).on("mouseleave", () => { cross.style("opacity", 0); hideTip(); });
    el.querySelector("ul").innerHTML = c.series.map((s) => `<li class="t-${s.tone}"><i></i>${esc(s.name)} <b>${d3.sum(s.values)}</b></li>`).join("");
  };

  // ------------------------------------------------------------------ partes de un total: barras ordenadas
  // (en lugar de anillos: se comparan de un vistazo y el total queda escrito arriba)
  function ranked(el, title, link, parts, unit) {
    const total = d3.sum(parts, (p) => p.value);
    const max = d3.max(parts, (p) => p.value) || 1;
    hbars(el, title, parts.filter((p) => p.value).sort((x, y) => y.value - x.value).map((p) => ({
      label: p.label, value: `${num(p.value)} (${pct(p.value, total)} %)`, pct: (p.value / max) * 100, tone: p.tone,
    })), link);
    el.querySelector(".sd-hbars")?.insertAdjacentHTML("beforebegin", `<p class="sd-total"><b>${num(total)}</b> ${esc(unit)}</p>`);
  }
  renderers.audits = (el, d) => {
    const a = d.overview?.audits;
    if (!a || !a.findings) return empty(el, "Hallazgos de auditoría", "Sin auditorías registradas.");
    ranked(el, "Hallazgos de auditoría", null, a.parts, "hallazgos");
    el.insertAdjacentHTML("beforeend", `<p class="sd-card-note">${a.audits} auditorías, ${a.closed} hallazgos cerrados y ${a.open} abiertos.${a.last ? ` Última: ${esc(a.last.type)} (${esc(a.last.date.split("-").reverse().join("/"))})` : ""}</p>`);
  };
  renderers.assets = (el, d) => {
    const a = d.overview?.assets;
    if (!a || !a.total) return empty(el, "Activos por clase", "Sin activos registrados.");
    ranked(el, "Activos por clase", d.links.assets, a.parts, "activos");
    el.insertAdjacentHTML("beforeend", `<p class="sd-card-note">${a.assigned} equipos asignados; ${a.review} no figuran en el último inventario.</p>`);
  };
  renderers.controls = (el, d) => {
    const c = d.overview?.controls;
    if (!c || !c.total) return empty(el, "Controles del Anexo A", "Sin controles registrados.");
    ranked(el, "Controles del Anexo A", d.links.annex, c.parts, "controles");
  };

  // ------------------------------------------------------------------ barras horizontales
  function hbars(el, title, rows, link) {
    el.innerHTML = `${cardHead(title, link)}<ul class="sd-hbars">${rows.map((r) => `<li class="t-${r.tone}">
      ${r.href ? `<a href="${esc(r.href)}">${esc(r.label)}${r.sub ? `<small>${esc(r.sub)}</small>` : ""}</a>` : `<span class="l">${esc(r.label)}${r.sub ? `<small>${esc(r.sub)}</small>` : ""}</span>`}
      <span class="sd-hbar"><i data-w="${Math.max(0, Math.min(100, r.pct))}"></i></span><span class="v">${esc(r.value)}</span></li>`).join("")}</ul>`;
    requestAnimationFrame(() => requestAnimationFrame(() => el.querySelectorAll("i[data-w]").forEach((i) => { i.style.width = `${i.dataset.w}%`; })));
  }
  renderers.documents = (el, d) => {
    const docs = d.overview?.documents;
    if (!docs) return empty(el, "Documentos que pide el Manual", "Sin datos.");
    hbars(el, "Documentos que pide el Manual", docs.rows.map((r) => ({
      label: `Cláusula ${r.clause}`, href: d.links.clause.replace("{c}", r.clause), value: `${r.found}/${r.total}`, pct: r.pct,
      tone: r.pct === 100 ? "ok" : r.pct >= 60 ? "warn" : "bad",
    })));
  };
  renderers.vulns = (el, d) => {
    const v = d.overview?.vulnerabilities;
    if (!v || !v.total) return empty(el, "Vulnerabilidades", "Sin vulnerabilidades registradas.");
    hbars(el, "Vulnerabilidades por severidad", v.rows.map((r) => ({ label: r.label, value: r.count, pct: r.pct, tone: r.tone })));
    el.insertAdjacentHTML("beforeend", '<p class="sd-card-note">Según el último inventario de Microsoft Defender de cada equipo. Falta verificar si ya se actualizaron.</p>');
  };
  renderers.factors = (el, d) => {
    if (!d.dataset) return empty(el, "Factores internos y externos", "Sin tablero cargado.");
    hbars(el, "Factores internos y externos", d.factors.map((f) => ({ label: f.label, sub: `${f.count} factores`, value: Number(f.value).toLocaleString("es-PE", { minimumFractionDigits: 2, maximumFractionDigits: 2 }), pct: (f.value / (d.averaged ? 6 : 4)) * 100, tone: f.tone })));
  };

  // ------------------------------------------------------------------ alineación: barras agrupadas y matrices
  renderers.osi = (el, d) => {
    if (!d.dataset) return empty(el, "Puntaje de cada objetivo de seguridad", "Sin tablero cargado.");
    el.innerHTML = `${cardHead("Puntaje de cada objetivo de seguridad")}<svg class="sd-chart"></svg><ul class="sd-legend"><li class="t-info"><i></i>Objetivos estratégicos</li><li class="t-calm"><i></i>Expectativas de partes interesadas</li></ul>`;
    const W = width(el) - 2, H = 200, m = { t: 16, r: 6, b: 24, l: 26 };
    const svg = d3.select(el.querySelector("svg")).attr("viewBox", `0 0 ${W} ${H}`);
    const x0 = d3.scaleBand().domain(d.osi_scores.map((s) => s.code)).range([m.l, W - m.r]).padding(0.28);
    const x1 = d3.scaleBand().domain(["oee", "req"]).range([0, x0.bandwidth()]).padding(0.12);
    const y = d3.scaleLinear().domain([0, d3.max(d.osi_scores, (s) => Math.max(s.oee, s.req)) || 1]).nice().range([H - m.b, m.t]);
    svg.append("g").attr("class", "grid").attr("transform", `translate(${m.l},0)`).call(d3.axisLeft(y).ticks(4).tickSize(-(W - m.l - m.r)).tickFormat(d3.format("d")));
    svg.append("g").attr("class", "axis").attr("transform", `translate(0,${H - m.b})`).call(d3.axisBottom(x0).tickSize(0).tickPadding(8)).select(".domain").remove();
    const g = svg.selectAll("g.o").data(d.osi_scores).join("g").attr("class", "o").attr("transform", (s) => `translate(${x0(s.code)},0)`);
    g.selectAll("rect").data((s) => [{ k: "oee", v: s.oee, s }, { k: "req", v: s.req, s }]).join("rect")
      .attr("class", (r) => `bar t-${r.k === "oee" ? "info" : "calm"}`).attr("x", (r) => x1(r.k)).attr("width", x1.bandwidth()).attr("rx", 1)
      .attr("y", y(0)).attr("height", 0)
      .on("mousemove", (ev, r) => showTip(`<b>${esc(r.s.code)}</b>. ${esc(r.s.description)}<br>Objetivos estratégicos: <b>${r.s.oee}</b><br>Partes interesadas: <b>${r.s.req}</b>`, ev))
      .on("mouseleave", hideTip)
      .transition().duration(DUR).delay((_, i) => i * 30).attr("y", (r) => y(r.v)).attr("height", (r) => y(0) - y(r.v));
  };

  function matrix(el, title, rows, security, kind) {
    const sum = state.data.summary[kind];
    const g = (state.data.links && state.data.links.gestionar) || {};
    const gestion = [kind === "oee" ? ["objetivos-estrategicos", "Objetivos estratégicos"] : ["expectativas", "Expectativas"], ["objetivos-seguridad", "Objetivos de seguridad"]]
      .filter(([k]) => g[k]).map(([k, t]) => `<a class="sd-gestion" href="${esc(g[k])}"><svg class="ico" aria-hidden="true"><use href="#i-plus"></use></svg>${esc(t)}</a>`).join("");
    el.innerHTML = `<div class="sd-card-head"><h3>${esc(title)}</h3>${gestion ? `<span class="sd-gestiones">${gestion}</span>` : ""}<span class="sd-state t-info">${sum[0]} de ${sum[1]} puntos mínimos</span></div>
      <div class="sd-matrix-wrap"><table class="sd-matrix"><thead><tr><th></th>${security.map((s, j) => `<th data-col="${j}" title="${esc(s.description)}">${esc(s.code)}</th>`).join("")}</tr></thead>
      <tbody>${rows.map((r, i) => `<tr data-row="${i}"><th title="${esc(r.text)}"><b>${i && rows[i - 1].code === r.code ? "" : esc(r.code)}</b>${esc(r.text)}</th>${r.cells.map((c, j) => `<td>${c
        ? (c.url ? `<button type="button" class="sd-cell r-${(c.rel || "n").toLowerCase()}" data-url="${esc(c.url)}" data-i="${i}" data-j="${j}">${esc(c.rel || "·")}</button>`
          : `<span class="sd-cell r-${(c.rel || "n").toLowerCase()}" data-i="${i}" data-j="${j}">${esc(c.rel || "·")}</span>`) : ""}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
    const table = el.querySelector("table");
    table.addEventListener("mouseover", (ev) => { // resaltado en cruz: fila y columna
      const c = ev.target.closest(".sd-cell"); if (!c) return;
      table.querySelectorAll(".is-hl, .is-cross").forEach((x) => x.classList.remove("is-hl", "is-cross"));
      table.querySelector(`thead th[data-col="${c.dataset.j}"]`)?.classList.add("is-hl");
      table.querySelector(`tr[data-row="${c.dataset.i}"] th`)?.classList.add("is-hl");
      table.querySelectorAll(`.sd-cell[data-j="${c.dataset.j}"], tr[data-row="${c.dataset.i}"] .sd-cell`).forEach((x) => x.classList.add("is-cross"));
    });
    table.addEventListener("mouseleave", () => table.querySelectorAll(".is-hl, .is-cross").forEach((x) => x.classList.remove("is-hl", "is-cross")));
  }
  renderers["oee-matrix"] = (el, d) => (d.dataset ? matrix(el, "Objetivos estratégicos vs objetivos de seguridad", d.oee_matrix, d.security, "oee") : empty(el, "Matriz OEE vs OSI", "Sin tablero cargado."));
  renderers["req-matrix"] = (el, d) => (d.dataset ? matrix(el, "Expectativas de partes interesadas vs objetivos de seguridad", d.req_matrix, d.security, "req") : empty(el, "Matriz EPI vs OSI", "Sin tablero cargado."));

  const setCell = (cell, rel) => { cell.textContent = rel || "·"; cell.className = `sd-cell r-${(rel || "n").toLowerCase()}`; };
  const cellByUrl = (url) => root.querySelector(`button.sd-cell[data-url="${CSS.escape(url)}"]`);
  const postRelation = async (url, rel) => {
    const body = new FormData();
    if (rel !== undefined) body.append("relation", rel);
    const res = await fetch(url, { method: "POST", credentials: "same-origin", headers: { "X-CSRFToken": csrf, Accept: "application/json" }, body });
    const data = await res.json();
    if (!res.ok || !data.ok) throw new Error(data.error || res.status);
    return data;
  };
  const applyChanged = (changed) => (changed || []).forEach((c) => {
    const el = cellByUrl(c.url);
    if (!el) return;
    setCell(el, c.relation);
    avisos()?.marcar(el);
  });
  async function undoChanges(changed) {
    const av = avisos();
    av?.guardando("Deshaciendo…");
    try {
      for (const c of changed) applyChanged((await postRelation(c.url, c.previous)).changed);
      av?.guardado({ texto: "Cambio deshecho" });
    } catch (e) {
      av?.error("No se pudo deshacer el cambio");
    }
    load({ force: true, quiet: true });
  }

  root.addEventListener("click", async (ev) => {
    const cell = ev.target.closest("button.sd-cell[data-url]");
    if (!cell || cell.classList.contains("is-pending")) return;
    const av = avisos();
    const prev = cell.textContent.trim().replace("·", "");
    setCell(cell, { "": "S", S: "P", P: "" }[prev] ?? "");
    cell.classList.add("is-pending");
    av?.guardando();
    try {
      const data = await postRelation(cell.dataset.url);
      cell.classList.remove("is-pending");
      applyChanged(data.changed);
      const col = state.data.security[Number(cell.dataset.j)]?.code || "";
      av?.guardado({ texto: `${col}: ${data.relation ? `relación «${data.relation}»` : "relación retirada"}`, deshacer: () => undoChanges(data.changed) });
      load({ force: true, quiet: true });
    } catch (e) {
      setCell(cell, prev);
      av?.marcar(cell, "error");
      av?.error("No se pudo guardar el cambio", { reintentar: () => cell.click() });
    }
  });

  // ------------------------------------------------------------------ matriz EFI / EFE
  // Igual que la hoja «EFIEFE» del Excel: eje horizontal = totales ponderados EFE (6 a la izquierda, 1 a la
  // derecha) y eje vertical = totales ponderados EFI (6 arriba, 1 abajo). El punto va en los totales calculados.
  renderers.ie = (el, d) => {
    if (!d.dataset) return empty(el, "Matriz EFI / EFE", "Sin tablero cargado.");
    const max = d.averaged ? 6 : 4, min = 1;
    const cut1 = min + (max - min) / 3, cut2 = min + 2 * (max - min) / 3;
    const zoneOf = (v) => (v >= cut2 ? 0 : v >= cut1 ? 1 : 2); // 0 alto, 1 medio, 2 bajo
    const ZONES = ["s", "s", "m", "s", "m", "w", "m", "w", "w"];
    const zone = ZONES[zoneOf(d.efi) * 3 + zoneOf(d.efe)];
    const verdict = { s: "Posición fuerte para crecer y construir", m: "Posición promedio para mantenerse", w: "Posición débil para cosechar o desinvertir" }[zone];
    el.innerHTML = `${cardHead("Matriz EFI / EFE")}
      <p class="sd-ie-verdict z-${zone}"><b>${verdict}</b>. EFE ${num(d.efe, 2)} y EFI ${num(d.efi, 2)}${d.efe > max || d.efi > max ? `; el gráfico llega hasta ${max}` : ""}.</p>
      <svg class="sd-chart sd-ie"></svg>
      <ul class="sd-legend"><li class="t-ok"><i></i>Crecer y construir</li><li class="t-warn"><i></i>Mantenerse</li><li class="t-bad"><i></i>Cosechar o desinvertir</li></ul>`;
    const W = Math.min(width(el) - 2, 560), H = 260, m = { t: 8, r: 8, b: 40, l: 44 };
    const svg = d3.select(el.querySelector("svg")).attr("viewBox", `0 0 ${W} ${H}`);
    const x = d3.scaleLinear().domain([max, min]).range([m.l, W - m.r]); // EFE: el máximo a la izquierda
    const y = d3.scaleLinear().domain([max, min]).range([m.t, H - m.b]); // EFI: el máximo arriba
    const cw = (W - m.l - m.r) / 3, ch = (H - m.t - m.b) / 3;
    svg.selectAll("rect.zone").data(ZONES).join("rect").attr("class", (z) => `zone z-${z}`)
      .attr("x", (_, i) => m.l + (i % 3) * cw + 2).attr("y", (_, i) => m.t + Math.floor(i / 3) * ch + 2).attr("width", cw - 4).attr("height", ch - 4).attr("rx", 3);
    svg.append("g").attr("class", "axis").attr("transform", `translate(0,${H - m.b + 4})`).call(d3.axisBottom(x).ticks(max - min).tickSize(0)).select(".domain").remove();
    svg.append("g").attr("class", "axis").attr("transform", `translate(${m.l - 6},0)`).call(d3.axisLeft(y).ticks(max - min).tickSize(0)).select(".domain").remove();
    const clamp = (v) => Math.max(min, Math.min(max, v));
    const px = Math.max(m.l + 10, Math.min(W - m.r - 10, x(clamp(d.efe))));
    const py = Math.max(m.t + 10, Math.min(H - m.b - 10, y(clamp(d.efi))));
    const cx = (m.l + W) / 2, cy = (m.t + H - m.b) / 2;
    const halo = svg.append("circle").attr("class", "pt-halo").attr("cx", reduce ? px : cx).attr("cy", reduce ? py : cy).attr("r", 14);
    const pt = svg.append("circle").attr("class", "pt").attr("cx", reduce ? px : cx).attr("cy", reduce ? py : cy).attr("r", 7);
    if (!reduce) [halo, pt].forEach((c) => c.transition("move").duration(DUR * 1.4).ease(d3.easeCubicOut).attr("cx", px).attr("cy", py));
    pt.on("mousemove", (ev) => showTip(`<b>${verdict}</b><br>EFE ${num(d.efe, 2)}, EFI ${num(d.efi, 2)}`, ev)).on("mouseleave", hideTip);
    svg.append("text").attr("class", "lab").attr("x", (m.l + W) / 2).attr("y", H - 4).attr("text-anchor", "middle").text("Totales ponderados EFE");
    svg.append("text").attr("class", "lab").attr("transform", `translate(12,${cy}) rotate(-90)`).attr("text-anchor", "middle").text("Totales ponderados EFI");
  };

  // ------------------------------------------------------------------ arranque
  load().then(schedule);
})();
