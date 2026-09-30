// Capa interactiva del mapa: riesgos por proceso, búsqueda, resaltado de relaciones
// y enlace directo (?proceso=<id>). Se apoya en processes_v71.js sin reemplazarlo.
document.addEventListener("DOMContentLoaded", () => {
    "use strict";

    const stage = document.querySelector("[data-process-stage]");
    const svg = document.querySelector("[data-process-lines]");
    const detail = document.querySelector("[data-process-detail]");
    const toolbar = document.querySelector(".process-map-toolbar");
    const dataEl = document.getElementById("process-data");
    if (!stage || !dataEl) return;

    const data = JSON.parse(dataEl.textContent);
    const relations = JSON.parse(document.getElementById("relation-data")?.textContent || "[]");
    const nodes = Array.from(stage.querySelectorAll(".process-node"));
    const LEVELS = ["Muy alto", "Alto", "Medio", "Bajo", "Muy bajo", "Pendiente"];
    const slug = (level) => (level || "ninguno").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/\s+/g, "-");
    const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;
    const esc = (value) => {
        const div = document.createElement("div");
        div.textContent = String(value ?? "");
        return div.innerHTML;
    };

    // ---- Distintivo de riesgo en cada proceso ----
    nodes.forEach((node) => {
        const summary = data[node.dataset.processId]?.risk_summary;
        if (!summary || node.classList.contains("process-party")) return;
        const total = LEVELS.reduce((sum, level) => sum + (summary.levels[level] || 0), 0);
        node.dataset.riskTop = slug(summary.top_level);
        node.dataset.riskTotal = String(total);
        node.dataset.missingControl = String(summary.missing_control);
        if (!total) return;
        const badge = document.createElement("span");
        badge.className = `node-risk level-${slug(summary.top_level)}`;
        badge.textContent = total;
        badge.title = `${plural(total, "riesgo", "riesgos")}, el más alto es ${summary.top_level.toLowerCase()}`;
        badge.setAttribute("aria-label", badge.title);
        node.appendChild(badge);
    });

    // ---- Herramientas: búsqueda, capa de riesgos y resaltado ----
    const tools = document.createElement("div");
    tools.className = "map-insight-tools";
    tools.innerHTML = `
        <label class="map-search">
            <span class="visually-hidden">Buscar proceso</span>
            <input type="search" placeholder="Buscar proceso (tecla /)" data-map-search autocomplete="off">
        </label>
        <label class="map-select">
            <span>Resaltar</span>
            <select data-map-highlight>
                <option value="">Nada</option>
                <option value="high">Riesgo alto o muy alto</option>
                <option value="missing">Tratamientos sin control del Anexo A</option>
                <option value="none">Procesos sin riesgos</option>
            </select>
        </label>
        <label class="map-toggle"><input type="checkbox" data-map-risk-layer checked> Riesgos en el mapa</label>
    `;
    toolbar?.insertBefore(tools, toolbar.querySelector(".map-tools"));

    const search = tools.querySelector("[data-map-search]");
    const highlight = tools.querySelector("[data-map-highlight]");
    const layer = tools.querySelector("[data-map-risk-layer]");

    function matches(node) {
        const term = search.value.trim().toLowerCase();
        const mode = highlight.value;
        const info = data[node.dataset.processId] || {};
        const text = `${info.name || ""} ${info.code || ""} ${info.responsible_area || ""}`.toLowerCase();
        if (term && !text.includes(term)) return false;
        if (mode === "high") return ["muy-alto", "alto"].includes(node.dataset.riskTop);
        if (mode === "missing") return Number(node.dataset.missingControl) > 0;
        if (mode === "none") return node.dataset.riskTotal === "0" || !node.dataset.riskTotal;
        return true;
    }

    function applyFilters() {
        const active = search.value.trim() || highlight.value;
        stage.classList.toggle("is-filtering", Boolean(active));
        nodes.forEach((node) => node.classList.toggle("is-match", Boolean(active) && matches(node)));
    }

    search.addEventListener("input", applyFilters);
    highlight.addEventListener("change", applyFilters);
    layer.addEventListener("change", () => stage.classList.toggle("hide-risk-layer", !layer.checked));
    search.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            const first = nodes.find((node) => node.classList.contains("is-match"));
            if (first) { first.focus(); first.click(); }
        }
    });

    // ---- Al pasar sobre un proceso: sus relaciones y procesos conectados ----
    function focusRelations(node) {
        const id = node?.dataset.processId;
        stage.classList.toggle("is-tracing", Boolean(id));
        const linked = new Set(id ? [id] : []);
        svg?.querySelectorAll("[data-dynamic-line]").forEach((path) => {
            const on = Boolean(id) && (path.dataset.source === id || path.dataset.target === id);
            path.classList.toggle("is-traced", on);
            if (on) { linked.add(path.dataset.source); linked.add(path.dataset.target); }
        });
        nodes.forEach((item) => item.classList.toggle("is-linked", linked.has(item.dataset.processId)));
    }
    nodes.forEach((node) => {
        node.addEventListener("mouseenter", () => focusRelations(node));
        node.addEventListener("focus", () => focusRelations(node));
        node.addEventListener("mouseleave", () => focusRelations(null));
        node.addEventListener("blur", () => focusRelations(null));
    });

    // ---- Riesgos en el panel de detalle ----
    function riskSection(id) {
        const info = data[id];
        const summary = info?.risk_summary;
        if (!summary || info.kind === "input" || info.kind === "output") return "";
        const total = LEVELS.reduce((sum, level) => sum + (summary.levels[level] || 0), 0);
        const url = info.risk_url;
        if (!total) {
            return `<section class="process-detail-section map-risk-section">
                <h3>Riesgos del proceso</h3>
                <p>Este proceso todavía no tiene riesgos vinculados.</p>
                <a class="outline-btn" href="${url}">Vincular desde la matriz</a>
            </section>`;
        }
        const bar = LEVELS.filter((level) => summary.levels[level])
            .map((level) => `<i class="level-${slug(level)}" style="flex:${summary.levels[level]}" title="${level}: ${summary.levels[level]}"></i>`).join("");
        const legend = LEVELS.filter((level) => summary.levels[level])
            .map((level) => `<span><i class="level-${slug(level)}"></i>${level} <b>${summary.levels[level]}</b></span>`).join("");
        const rows = summary.items.map((item) => `
            <a class="map-risk-row" href="${item.url}">
                <span class="level-chip level-${slug(item.level)}">${esc(item.level)}</span>
                <b>${esc(item.code)}</b>
                <span class="map-risk-event">${esc(item.event)}</span>
                <small>${esc(item.type)}, ${plural(item.treatments, "tratamiento", "tratamientos")}</small>
            </a>`).join("");
        const annex = summary.annex_controls.length
            ? `<div class="annex-chips">${summary.annex_controls.map((c) => `<span title="${esc(c.name)}">A.${esc(c.code)}</span>`).join("")}</div>`
            : "<p>Sin controles del Anexo A asociados.</p>";
        const warning = summary.missing_control
            ? `<p class="map-risk-warning">${summary.missing_control === 1 ? "Un tratamiento elige controles pero no indica" : `${summary.missing_control} tratamientos eligen controles pero no indican`} cuál del Anexo A.</p>`
            : "";
        return `<section class="process-detail-section map-risk-section">
            <h3>Riesgos del proceso <span>${total}</span></h3>
            <div class="risk-bar" role="img" aria-label="Distribución por nivel de riesgo">${bar}</div>
            <div class="risk-legend">${legend}</div>
            <div class="map-risk-list">${rows}</div>
            ${total > summary.items.length ? `<a class="map-risk-more" href="${url}">Ver los ${total} riesgos en la matriz</a>` : `<a class="map-risk-more" href="${url}">Abrir matriz filtrada</a>`}
            <h3>Controles del Anexo A</h3>
            ${annex}
            ${warning}
        </section>`;
    }

    function enhance(id) {
        const content = detail?.querySelector(".process-detail-content");
        if (!content || content.dataset.enhanced === id) return;
        content.dataset.enhanced = id;
        const header = content.querySelector(".process-detail-actions");
        header?.insertAdjacentHTML("afterend", riskSection(id));
        const url = new URL(window.location.href);
        url.searchParams.set("proceso", id);
        window.history.replaceState(null, "", url);
    }

    nodes.forEach((node) => node.addEventListener("click", () => enhance(node.dataset.processId)));

    // ---- Atajos de teclado ----
    document.addEventListener("keydown", (event) => {
        const typing = /INPUT|TEXTAREA|SELECT/.test(document.activeElement?.tagName || "");
        if (event.key === "/" && !typing) { event.preventDefault(); search.focus(); }
        if (event.key === "Escape") {
            search.value = "";
            highlight.value = "";
            applyFilters();
            focusRelations(null);
        }
    });

    // ---- Enlace directo: /procesos/?proceso=<id> ----
    const wanted = new URLSearchParams(window.location.search).get("proceso");
    const start = nodes.find((node) => node.dataset.processId === wanted) || stage.querySelector(".process-node.selected");
    if (start) {
        if (wanted) start.click();
        enhance(start.dataset.processId);
    }
});
