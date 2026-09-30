// Organigrama interactivo: se mueve arrastrando, se acerca con la rueda o el gesto de pellizco,
// encuadra solo al abrir y, al hacer clic en un puesto, muestra su cadena de mando y de qué es responsable.
document.addEventListener("DOMContentLoaded", () => {
    "use strict";

    const root = document.querySelector("[data-oc]");
    const viewport = root?.querySelector("[data-oc-viewport]");
    const stage = root?.querySelector("[data-oc-stage]");
    if (!root || !viewport || !stage) return;

    const pct = root.querySelector("[data-oc-pct]");
    const panel = root.querySelector("[data-oc-panel]");
    const body = root.querySelector("[data-oc-body]");
    const hint = root.querySelector(".oc-hint");
    const MIN = 0.15;
    const MAX = 1.8;
    let s = 1;
    let tx = 0;
    let ty = 0;

    // ---------- Transformación ----------
    function render(animate) {
        stage.classList.toggle("is-animating", Boolean(animate));
        stage.style.transform = `translate(${tx}px, ${ty}px) scale(${s})`;
        if (pct) pct.textContent = `${Math.round(s * 100)}%`;
        if (animate) setTimeout(() => stage.classList.remove("is-animating"), 400);
    }
    const clamp = (v) => Math.min(MAX, Math.max(MIN, v));

    function zoomAt(factor, cx, cy, animate) {
        const ns = clamp(s * factor);
        tx = cx - (cx - tx) * (ns / s);
        ty = cy - (cy - ty) * (ns / s);
        s = ns;
        render(animate);
    }

    function size() {
        return { w: stage.offsetWidth, h: stage.offsetHeight };
    }

    function fit(animate) {
        const { w, h } = size();
        const vw = viewport.clientWidth;
        const vh = viewport.clientHeight;
        s = clamp(Math.min(1, (vw - 60) / w, (vh - 110) / h));
        tx = (vw - w * s) / 2;
        ty = Math.max(20, (vh - h * s) / 2);
        render(animate);
    }

    function centerOf(el) {
        const r = el.getBoundingClientRect();
        const v = viewport.getBoundingClientRect();
        return { x: (r.left + r.width / 2 - v.left - tx) / s, y: (r.top + r.height / 2 - v.top - ty) / s };
    }

    function flyTo(el, scale) {
        const c = centerOf(el);
        s = clamp(Math.max(s, scale || 0.9));
        tx = viewport.clientWidth / 2 - c.x * s - (panel && !panel.hidden ? 180 : 0);
        ty = viewport.clientHeight / 2 - c.y * s;
        render(true);
    }

    function dismissHint() {
        if (hint && !hint.classList.contains("is-gone")) hint.classList.add("is-gone");
    }

    // ---------- Rueda y gesto de pellizco ----------
    viewport.addEventListener("wheel", (event) => {
        event.preventDefault();
        dismissHint();
        const v = viewport.getBoundingClientRect();
        const speed = event.ctrlKey ? 0.012 : 0.0016;
        zoomAt(Math.exp(-event.deltaY * speed), event.clientX - v.left, event.clientY - v.top);
    }, { passive: false });

    // ---------- Arrastrar para moverse (ratón, lápiz y táctil) ----------
    const pointers = new Map();
    let last = null;
    let moved = 0;
    let pinch = null;
    const interactive = "a, button, input, select, textarea, form, [data-node-menu]";

    viewport.addEventListener("pointerdown", (event) => {
        if (event.target.closest(interactive)) return;
        pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
        last = { x: event.clientX, y: event.clientY };
        moved = 0;
        if (pointers.size === 2) {
            const [a, b] = [...pointers.values()];
            pinch = { d: Math.hypot(a.x - b.x, a.y - b.y), s };
        }
    });
    viewport.addEventListener("pointermove", (event) => {
        if (!pointers.has(event.pointerId)) return;
        pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
        if (pointers.size === 2 && pinch) {
            const [a, b] = [...pointers.values()];
            const v = viewport.getBoundingClientRect();
            const d = Math.hypot(a.x - b.x, a.y - b.y);
            zoomAt((pinch.s * d / pinch.d) / s, (a.x + b.x) / 2 - v.left, (a.y + b.y) / 2 - v.top);
            return;
        }
        const dx = event.clientX - last.x;
        const dy = event.clientY - last.y;
        moved += Math.abs(dx) + Math.abs(dy);
        if (moved > 4 && !viewport.classList.contains("is-panning")) {
            // La captura empieza al arrastrar, así un clic simple sigue llegando al puesto.
            viewport.classList.add("is-panning");
            try { viewport.setPointerCapture(event.pointerId); } catch (e) { /* puntero ya liberado */ }
            dismissHint();
        }
        tx += dx;
        ty += dy;
        last = { x: event.clientX, y: event.clientY };
        render(false);
    });
    const release = (event) => {
        pointers.delete(event.pointerId);
        if (pointers.size < 2) pinch = null;
        if (!pointers.size) setTimeout(() => viewport.classList.remove("is-panning"), 0);
    };
    viewport.addEventListener("pointerup", release);
    viewport.addEventListener("pointercancel", release);

    viewport.addEventListener("dblclick", (event) => {
        if (!event.target.closest(".org-node")) fit(true);
    });

    viewport.addEventListener("keydown", (event) => {
        const cx = viewport.clientWidth / 2;
        const cy = viewport.clientHeight / 2;
        if (event.target !== viewport) return;
        if (event.key === "+" || event.key === "=") zoomAt(1.2, cx, cy, true);
        else if (event.key === "-") zoomAt(1 / 1.2, cx, cy, true);
        else if (event.key === "0") fit(true);
        else if (event.key.startsWith("Arrow")) {
            const step = 60;
            if (event.key === "ArrowLeft") tx += step;
            if (event.key === "ArrowRight") tx -= step;
            if (event.key === "ArrowUp") ty += step;
            if (event.key === "ArrowDown") ty -= step;
            render(true);
        } else return;
        event.preventDefault();
    });

    root.querySelectorAll("[data-oc-zoom]").forEach((b) => b.addEventListener("click", () => {
        zoomAt(Number(b.dataset.ocZoom) > 0 ? 1.25 : 0.8, viewport.clientWidth / 2, viewport.clientHeight / 2, true);
    }));
    root.querySelector("[data-oc-fit]")?.addEventListener("click", () => fit(true));

    // ---------- Ramas ----------
    function setBranch(item, open) {
        item.classList.toggle("branch-collapsed", !open);
        const t = item.querySelector(":scope > article > [data-collapse-branch]");
        if (t) t.setAttribute("aria-expanded", String(open));
    }
    root.querySelectorAll("[data-collapse-branch]").forEach((button) => {
        button.addEventListener("click", (event) => {
            event.stopPropagation();
            const item = button.closest(".org-node-item");
            if (item) setBranch(item, item.classList.contains("branch-collapsed"));
        });
    });
    root.querySelector("[data-oc-expand]")?.addEventListener("click", () => {
        root.querySelectorAll(".org-node-item.branch-collapsed").forEach((item) => setBranch(item, true));
        requestAnimationFrame(() => fit(true));
    });
    function openAncestors(node) {
        let item = node.closest(".org-node-item")?.parentElement?.closest(".org-node-item");
        while (item) { setBranch(item, true); item = item.parentElement.closest(".org-node-item"); }
    }

    // ---------- Menú de cada puesto ----------
    root.querySelectorAll("[data-node-menu-button]").forEach((button) => {
        button.addEventListener("click", (event) => {
            event.stopPropagation();
            root.querySelectorAll(".node-menu.open").forEach((m) => { if (m !== button.closest(".node-menu")) m.classList.remove("open"); });
            button.closest(".node-menu")?.classList.toggle("open");
        });
    });
    document.addEventListener("click", () => root.querySelectorAll(".node-menu.open").forEach((m) => m.classList.remove("open")));
    root.querySelectorAll("[data-node-menu]").forEach((m) => m.addEventListener("click", (e) => e.stopPropagation()));

    // ---------- Búsqueda y filtro por área ----------
    const search = root.querySelector("[data-oc-search]");
    const area = root.querySelector("[data-oc-area]");
    const result = root.querySelector("[data-oc-result]");
    const nodes = Array.from(root.querySelectorAll("[data-org-node]"));
    const norm = (t) => t.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
    let matches = [];
    let cursor = 0;
    function runSearch() {
        const q = norm(search?.value.trim() || "");
        const a = area?.value || "";
        const active = Boolean(q || a);
        matches = [];
        nodes.forEach((node) => {
            const ok = (!q || norm(node.textContent).includes(q)) && (!a || node.dataset.area === a);
            node.classList.toggle("org-match", active && ok);
            node.classList.toggle("org-muted", active && !ok);
            if (active && ok) matches.push(node);
        });
        root.classList.toggle("is-filtering", active);
        if (result) result.textContent = active ? (matches.length === 1 ? "1 puesto" : `${matches.length} puestos`) : "";
        cursor = 0;
        if (matches[0]) { openAncestors(matches[0]); requestAnimationFrame(() => flyTo(matches[0], 0.9)); }
    }
    let timer = null;
    search?.addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(runSearch, 180); });
    search?.addEventListener("keydown", (event) => {
        if (event.key === "Enter" && matches.length) {
            event.preventDefault();
            cursor = (cursor + 1) % matches.length;
            openAncestors(matches[cursor]);
            flyTo(matches[cursor], 0.9);
        }
    });
    area?.addEventListener("change", runSearch);

    // ---------- Trazabilidad del puesto ----------
    const esc = (v) => { const d = document.createElement("div"); d.textContent = String(v ?? ""); return d.innerHTML; };
    let selected = null;
    let request = 0;

    function clearPath() {
        root.querySelectorAll(".is-selected, .is-path").forEach((el) => el.classList.remove("is-selected", "is-path"));
        root.querySelectorAll(".on-path").forEach((el) => el.classList.remove("on-path"));
        root.classList.remove("has-selection");
    }
    function markPath(node) {
        clearPath();
        node.classList.add("is-selected");
        root.classList.add("has-selection");
        let item = node.closest(".org-node-item");
        while (item) {
            item.classList.add("on-path");
            const art = item.querySelector(":scope > article");
            if (art && art !== node) art.classList.add("is-path");
            item = item.parentElement.closest(".org-node-item");
        }
    }

    function skeleton() {
        return `<div class="oc-skel"><i class="skel-l h"></i><i class="skel-l w60"></i><i class="skel-l gap w90"></i><i class="skel-l w75"></i><i class="skel-l gap w90"></i><i class="skel-l w60"></i><i class="skel-l w75"></i></div>`;
    }
    function list(title, items, fmt, empty) {
        return `<section class="oc-sec"><h4>${title}${items.length ? ` <small>${items.length}</small>` : ""}</h4>${items.length ? `<ul>${items.map(fmt).join("")}</ul>` : `<p class="oc-empty">${empty}</p>`}</section>`;
    }
    function link(url, text) { return url ? `<a href="${url}">${text}</a>` : `<span>${text}</span>`; }

    function show(data) {
        const chain = data.chain.slice().reverse();
        body.innerHTML = `
            <div class="oc-title">
                <h3>${esc(data.title)}</h3>
                <p>${esc(data.code)}${data.area ? ` · ${esc(data.area)}` : " · Sin área"}${data.critical ? ' · <b class="oc-crit">Puesto crítico</b>' : ""}</p>
            </div>
            ${chain.length ? `<section class="oc-sec"><h4>Cadena de mando</h4><ol class="oc-chain">${chain.map((c) => `<li><button type="button" data-goto="${c.id}">${esc(c.title)}</button></li>`).join("")}<li><b>${esc(data.title)}</b></li></ol></section>` : ""}
            ${list("Personas en el puesto", data.people, (p) => `<li>${link(p.url, `<b>${esc(p.name)}</b>`)}<small>${esc(p.code)}${p.since ? ` · desde ${esc(p.since)}` : ""}</small></li>`, "Puesto vacante.")}
            ${list("Puestos a cargo", data.reports, (r) => `<li><button type="button" data-goto="${r.id}">${esc(r.title)}</button></li>`, "No tiene puestos a cargo.")}
            ${list("Procesos", data.processes, (p) => `<li>${link(p.url, `<b>${esc(p.code)}</b> ${esc(p.name)}`)}<small>${esc(p.role)}</small></li>`, "No es dueño ni participa en procesos del mapa.")}
            ${list(`Riesgos a su cargo${data.risk_total > data.risks.length ? ` (se muestran ${data.risks.length} de ${data.risk_total})` : ""}`, data.risks, (r) => `<li>${link(r.url, `<b>${esc(r.code)}</b> ${esc(r.name)}`)}${r.process ? `<small>${esc(r.process)}</small>` : ""}</li>`, "No tiene riesgos asignados.")}
            ${list("Tratamientos a su cargo", data.treatments, (t) => `<li><span><b>${esc(t.risk)}</b> ${esc(t.action)}</span><small>${esc(t.status)}${t.due ? ` · vence ${esc(t.due)}` : ""}</small></li>`, "No es responsable de tratamientos.")}
            ${list("Documentos de los que es propietario", data.documents_owned, (d) => `<li>${link(d.url, esc(d.title))}${d.verified ? "" : "<small>Sin verificar</small>"}</li>`, "No figura como propietario de documentos.")}
            ${list("Autorizaciones documentales", data.documents_access, (d) => `<li>${link(d.url, esc(d.title))}</li>`, "Sin autorizaciones registradas.")}`;
        body.classList.remove("is-entering"); void body.offsetWidth; body.classList.add("is-entering");
    }

    async function select(node) {
        selected = node;
        dismissHint();
        markPath(node);
        panel.hidden = false;
        requestAnimationFrame(() => panel.classList.add("is-open"));
        body.innerHTML = skeleton();
        flyTo(node, Math.max(s, 0.8));
        const id = ++request;
        try {
            const res = await fetch(node.dataset.traceUrl, { headers: { Accept: "application/json" } });
            if (!res.ok) throw new Error(res.status);
            const data = await res.json();
            if (id === request) show(data);
        } catch (e) {
            if (id === request) body.innerHTML = '<p class="oc-empty">No se pudo cargar la trazabilidad de este puesto. Intente de nuevo.</p>';
        }
    }
    function close() {
        panel.classList.remove("is-open");
        setTimeout(() => { panel.hidden = true; }, 200);
        clearPath();
        selected = null;
    }

    nodes.forEach((node) => {
        node.addEventListener("click", (event) => {
            if (event.target.closest(interactive) || viewport.classList.contains("is-panning") || moved > 4) return;
            select(node);
        });
        node.addEventListener("keydown", (event) => {
            if ((event.key === "Enter" || event.key === " ") && event.target === node) { event.preventDefault(); select(node); }
        });
    });
    body?.addEventListener("click", (event) => {
        const go = event.target.closest("[data-goto]");
        if (!go) return;
        const node = root.querySelector(`[data-org-node="${go.dataset.goto}"]`);
        if (node) { openAncestors(node); select(node); }
    });
    root.querySelector("[data-oc-close]")?.addEventListener("click", close);
    document.addEventListener("keydown", (event) => { if (event.key === "Escape" && selected) close(); });

    // ---------- Inicio: encuadre automático ----------
    const start = () => fit(false);
    if (document.fonts?.ready) document.fonts.ready.then(start); else start();
    let resizeTimer = null;
    window.addEventListener("resize", () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(() => fit(false), 200); });
    setTimeout(dismissHint, 9000);
});
