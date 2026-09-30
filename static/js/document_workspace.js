// Ficha de documento y visor de hojas: pestañas, vista previa diferida, hojas de Excel y subida.
document.addEventListener("DOMContentLoaded", () => {
    "use strict";

    // Pestañas de la ficha
    const tabs = Array.from(document.querySelectorAll("[data-dw-tab]"));
    const panels = Array.from(document.querySelectorAll("[data-dw-panel]"));
    function show(name) {
        tabs.forEach((t) => t.classList.toggle("is-active", t.dataset.dwTab === name));
        panels.forEach((p) => {
            const on = p.dataset.dwPanel === name;
            p.hidden = !on;
            if (on) { p.classList.remove("is-entering"); void p.offsetWidth; p.classList.add("is-entering"); }
        });
        if (name === "preview") loadPreview();
    }
    tabs.forEach((t) => t.addEventListener("click", () => show(t.dataset.dwTab)));

    // PDF: se pide solo cuando la vista previa está a la vista.
    function loadPreview() {
        const frame = document.querySelector("iframe[data-dw-src]");
        if (!frame || frame.src) return;
        const loading = document.querySelector("[data-dw-loading]");
        frame.addEventListener("load", () => { if (loading) loading.hidden = true; }, { once: true });
        frame.src = frame.dataset.dwSrc;
    }
    if (document.querySelector("[data-dw-panel='preview']:not([hidden])")) loadPreview();

    // Hojas de cálculo: pestañas y búsqueda
    document.querySelectorAll("[data-xl]").forEach((xl) => {
        const sheets = Array.from(xl.querySelectorAll("[data-xl-sheet]"));
        const sheetTabs = Array.from(xl.querySelectorAll("[data-xl-tab]"));
        const search = xl.querySelector("[data-xl-search]");
        const count = xl.querySelector("[data-xl-count]");
        const active = () => sheets.find((s) => !s.hidden);
        function filter() {
            const term = (search?.value || "").trim().toLowerCase();
            const sheet = active();
            if (!sheet) return;
            let hits = 0;
            sheet.querySelectorAll("tbody tr").forEach((tr) => {
                const ok = !term || tr.textContent.toLowerCase().includes(term);
                tr.hidden = !ok;
                if (ok && term) hits += 1;
            });
            if (count) count.textContent = term ? (hits === 1 ? "1 fila" : `${hits} filas`) : "";
        }
        sheetTabs.forEach((tab) => tab.addEventListener("click", () => {
            sheets.forEach((s) => { s.hidden = s.dataset.xlSheet !== tab.dataset.xlTab; });
            sheetTabs.forEach((t) => t.classList.toggle("is-active", t === tab));
            filter();
        }));
        search?.addEventListener("input", filter);
    });

    // Subida de versión
    const form = document.querySelector("[data-dw-upload]");
    if (form) {
        const input = form.querySelector("[data-dw-file]");
        const drop = form.querySelector("[data-dw-drop]");
        const text = form.querySelector("[data-dw-drop-text]");
        const sizeText = (n) => (n > 1048576 ? `${(n / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1024))} KB`);
        input?.addEventListener("change", () => {
            const file = input.files[0];
            drop.classList.toggle("has-file", Boolean(file));
            text.textContent = file ? `${file.name} (${sizeText(file.size)})` : "Arrastre el archivo aquí o haga clic para elegirlo";
        });
        ["dragenter", "dragover"].forEach((e) => drop?.addEventListener(e, (ev) => { ev.preventDefault(); drop.classList.add("is-over"); }));
        ["dragleave", "drop"].forEach((e) => drop?.addEventListener(e, () => drop.classList.remove("is-over")));
        drop?.addEventListener("drop", (ev) => {
            ev.preventDefault();
            if (ev.dataTransfer.files.length) { input.files = ev.dataTransfer.files; input.dispatchEvent(new Event("change")); }
        });
        form.addEventListener("submit", () => {
            const overlay = form.querySelector("[data-dw-uploading]");
            if (overlay) overlay.hidden = false;
            window.SGSILoader?.mount(overlay?.querySelector("[data-sgsi-loader]"));
        });
        document.querySelectorAll("[data-open-upload]").forEach((a) => a.addEventListener("click", (ev) => {
            ev.preventDefault();
            form.scrollIntoView({ behavior: "smooth", block: "start" });
            form.classList.remove("is-flash"); void form.offsetWidth; form.classList.add("is-flash");
            setTimeout(() => input?.focus(), 250);
        }));
    }
});
