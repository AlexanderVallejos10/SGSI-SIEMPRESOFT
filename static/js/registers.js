// Registros del SGSI: edición en línea (texto, fechas, listas, meses y ¿cumple?), filas nuevas,
// búsqueda, pestañas e indicadores que se actualizan al guardar.
document.addEventListener("DOMContentLoaded", () => {
    "use strict";
    const csrf = document.querySelector("[data-csrf] input")?.value || "";
    const post = async (url, body) => {
        const res = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json", "X-CSRFToken": csrf, Accept: "application/json" },
            body: JSON.stringify(body || {}),
        });
        if (!res.ok) throw new Error(res.status);
        return res.json();
    };

    // ---------- indicadores ----------
    function refresh(summary) {
        if (!summary) return;
        (summary.cards || []).forEach((c, i) => {
            const b = document.querySelector(`[data-kpi="${i}"]`);
            if (b && b.textContent !== String(c.value)) { b.textContent = c.value; b.classList.remove("is-bump"); void b.offsetWidth; b.classList.add("is-bump"); }
            const h = document.querySelector(`[data-kpi-hint="${i}"]`);
            if (h && c.hint) h.textContent = c.hint;
        });
        const bar = document.querySelector("[data-kpi-bar]");
        if (bar) bar.style.setProperty("--p", `${summary.progress}%`);
        const pct = document.querySelector("[data-kpi-pct]");
        if (pct) pct.textContent = summary.progress;
        document.querySelectorAll(".rg-heat-col").forEach((col, i) => {
            const m = (summary.months || [])[i];
            if (!m) return;
            col.querySelector("i").style.setProperty("--p", `${m.pct}%`);
            col.querySelector("b").textContent = m.count;
        });
    }

    function flash(row, ok) {
        row.classList.remove("is-saved", "is-error"); void row.offsetWidth;
        row.classList.add(ok ? "is-saved" : "is-error");
    }

    async function save(row, changes) {
        row.classList.add("is-saving");
        try {
            const data = await post(row.dataset.update, changes);
            const tmp = document.createElement("tbody");
            tmp.innerHTML = data.html.trim();
            const fresh = tmp.firstElementChild;
            row.replaceWith(fresh);
            flash(fresh, true);
            refresh(data.summary);
            return fresh;
        } catch (e) {
            row.classList.remove("is-saving");
            flash(row, false);
        }
    }

    // ---------- celdas de texto y fecha ----------
    function edit(cell) {
        if (cell.querySelector("input, textarea")) return;
        const row = cell.closest(".rg-row");
        const field = cell.dataset.edit;
        const type = cell.dataset.type;
        const original = cell.dataset.value ?? (cell.textContent.trim() === "—" ? "" : cell.textContent.trim());
        const input = document.createElement(type === "longtext" ? "textarea" : "input");
        if (type === "date") input.type = "date";
        input.className = "rg-input";
        input.value = original;
        if (type === "longtext") input.rows = Math.max(2, Math.ceil(original.length / 60));
        cell.textContent = "";
        cell.appendChild(input);
        cell.classList.add("is-editing");
        input.focus();
        input.select?.();
        let done = false;
        const finish = (commit) => {
            if (done) return;
            done = true;
            const value = input.value.trim();
            if (commit && value !== original) save(row, { [field]: value });
            else { cell.classList.remove("is-editing"); cell.textContent = original || "—"; }
        };
        input.addEventListener("blur", () => finish(true));
        input.addEventListener("keydown", (ev) => {
            if (ev.key === "Escape") { ev.preventDefault(); finish(false); }
            if (ev.key === "Enter" && (type !== "longtext" || !ev.shiftKey)) { ev.preventDefault(); finish(true); }
        });
    }

    document.addEventListener("click", (ev) => {
        const cell = ev.target.closest(".rg-cell[tabindex]");
        if (cell && !ev.target.closest("input, textarea")) edit(cell);
    });
    document.addEventListener("keydown", (ev) => {
        const cell = ev.target.closest?.(".rg-cell[tabindex]");
        if (cell && (ev.key === "Enter" || ev.key === "F2") && !cell.querySelector("input, textarea")) { ev.preventDefault(); edit(cell); }
    });

    // ---------- listas, meses y ¿cumple? ----------
    document.addEventListener("change", (ev) => {
        const sel = ev.target.closest("select[data-edit]");
        if (sel) save(sel.closest(".rg-row"), { [sel.dataset.edit]: sel.value });
    });
    document.addEventListener("click", (ev) => {
        const month = ev.target.closest(".rg-m");
        if (month && !month.disabled) {
            month.classList.toggle("is-on");
            const row = month.closest(".rg-row");
            const months = [...row.querySelectorAll(".rg-m.is-on")].map((b) => Number(b.dataset.month));
            save(row, { meses: months });
            return;
        }
        const seg = ev.target.closest("[data-set]");
        if (seg && !seg.disabled) save(seg.closest(".rg-row"), { [seg.dataset.set]: seg.dataset.value });
    });

    // ---------- quitar fila ----------
    document.addEventListener("click", async (ev) => {
        const del = ev.target.closest("[data-del]");
        if (!del) return;
        const row = del.closest(".rg-row");
        const label = row.querySelector(".rg-cell")?.textContent.trim().slice(0, 60) || "esta fila";
        if (!window.confirm(`¿Quitar «${label}» del registro?`)) return;
        try {
            const data = await post(row.dataset.delete);
            row.classList.add("is-leaving");
            setTimeout(() => row.remove(), 220);
            refresh(data.summary);
        } catch (e) { flash(row, false); }
    });

    // ---------- agregar fila ----------
    document.addEventListener("click", async (ev) => {
        const add = ev.target.closest("[data-add]");
        if (!add) return;
        const sheet = add.closest("[data-section]");
        const layoutTable = sheet.querySelector(".rg-table");
        const newGroup = sheet.querySelector("[data-new-group]");
        const group = add.dataset.groupValue || newGroup?.value.trim() || "";
        const data = {};
        if (group) data.perfil = group;
        try {
            const res = await post(sheet.dataset.create, { section: sheet.dataset.section, year: Number(sheet.dataset.year) || null, data });
            let body = [...sheet.querySelectorAll("tbody[data-group]")].find((b) => b.dataset.group === group);
            if (!body) {
                sheet.querySelector(".rg-empty")?.closest("tbody")?.remove();
                body = document.createElement("tbody");
                body.dataset.group = group;
                if (group) {
                    const cols = layoutTable.querySelector("thead tr").children.length;
                    body.innerHTML = `<tr class="rg-group"><th colspan="${cols}"><span></span><small>1</small></th></tr>`;
                    body.querySelector("span").textContent = group;
                }
                layoutTable.appendChild(body);
            }
            const tmp = document.createElement("tbody");
            tmp.innerHTML = res.html.trim();
            const row = tmp.firstElementChild;
            body.appendChild(row);
            row.classList.add("is-new");
            if (newGroup) newGroup.value = "";
            refresh(res.summary);
            const first = row.querySelector(".rg-cell[tabindex]");
            if (first) { row.scrollIntoView({ behavior: "smooth", block: "center" }); edit(first); }
        } catch (e) { window.alert("No se pudo agregar la fila. Intente de nuevo."); }
    });

    // ---------- pestañas, búsqueda y filtro de estado ----------
    const tabs = [...document.querySelectorAll("[data-tab]")];
    tabs.forEach((t) => t.addEventListener("click", () => {
        tabs.forEach((x) => x.classList.toggle("is-active", x === t));
        document.querySelectorAll("[data-section]").forEach((s) => { s.hidden = s.dataset.section !== t.dataset.tab; });
    }));
    const search = document.querySelector("[data-search]");
    let state = "";
    function filter() {
        const q = (search?.value || "").trim().toLowerCase();
        document.querySelectorAll(".rg-row").forEach((row) => {
            const okText = !q || row.textContent.toLowerCase().includes(q);
            const okState = !state || row.dataset.state === state;
            row.hidden = !(okText && okState);
        });
        document.querySelectorAll("tbody[data-group]").forEach((b) => {
            const head = b.querySelector(".rg-group");
            if (head) head.hidden = ![...b.querySelectorAll(".rg-row")].some((r) => !r.hidden);
        });
    }
    search?.addEventListener("input", filter);
    document.querySelectorAll("[data-filter]").forEach((b) => b.addEventListener("click", () => {
        state = b.dataset.filter;
        document.querySelectorAll("[data-filter]").forEach((x) => x.classList.toggle("is-active", x === b));
        filter();
    }));

    // ---------- importar ----------
    const dialog = document.querySelector("[data-import-dialog]");
    document.querySelector("[data-open-import]")?.addEventListener("click", () => dialog?.showModal());
    document.querySelectorAll("[data-close-import]").forEach((b) => b.addEventListener("click", () => dialog?.close()));
});
