// Página de cláusula: navegación entre numerales, requisitos plegables animados y visor de PDF.
document.addEventListener("DOMContentLoaded", () => {
    "use strict";
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    // Tarjetas: aparecen al entrar en pantalla.
    const cards = Array.from(document.querySelectorAll("[data-nm]"));
    if ("IntersectionObserver" in window && !reduce) {
        cards.forEach((card) => card.classList.add("is-waiting"));
        const reveal = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) { entry.target.classList.remove("is-waiting"); reveal.unobserve(entry.target); }
            });
        }, { rootMargin: "0px 0px -8% 0px" });
        cards.forEach((card) => reveal.observe(card));
    }

    // Navegación: marca el numeral que se está leyendo.
    const links = Array.from(document.querySelectorAll("[data-nm-link]"));
    if (links.length && "IntersectionObserver" in window) {
        const spy = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (!entry.isIntersecting) return;
                links.forEach((a) => a.classList.toggle("is-active", a.dataset.nmLink === entry.target.id));
            });
        }, { rootMargin: "-30% 0px -60% 0px" });
        cards.forEach((card) => spy.observe(card));
    }
    links.forEach((a) => a.addEventListener("click", (event) => {
        const target = document.getElementById(a.dataset.nmLink);
        if (!target) return;
        event.preventDefault();
        target.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
        history.replaceState(null, "", `#${target.id}`);
        target.classList.remove("is-flash"); void target.offsetWidth; target.classList.add("is-flash");
    }));

    // Requisitos de la norma: apertura y cierre con altura animada.
    document.querySelectorAll("[data-nm-norm]").forEach((details) => {
        const summary = details.querySelector("summary");
        const body = details.querySelector(".nm-norm-body");
        summary.addEventListener("click", (event) => {
            if (reduce || !body) return;
            event.preventDefault();
            if (details.open) {
                body.style.height = `${body.scrollHeight}px`;
                requestAnimationFrame(() => { body.style.height = "0px"; });
                body.addEventListener("transitionend", () => { details.open = false; body.style.height = ""; }, { once: true });
            } else {
                details.open = true;
                body.style.height = "0px";
                requestAnimationFrame(() => { body.style.height = `${body.scrollHeight}px`; });
                body.addEventListener("transitionend", () => { body.style.height = ""; }, { once: true });
            }
        });
    });

    // Visor de PDF.
    const drawer = document.querySelector("[data-pdf-drawer]");
    const backdrop = document.querySelector("[data-pdf-backdrop]");
    const viewer = drawer?.querySelector("[data-pdf-viewer]");
    let opener = null;
    function openPdf(button) {
        opener = button;
        const url = button.dataset.openPdf;
        drawer.querySelector("[data-pdf-title]").textContent = button.dataset.title || "Documento";
        if (viewer) {
            viewer.dataset.title = button.dataset.title || "Documento";
            viewer.querySelector(".pv-title").textContent = viewer.dataset.title;
            viewer.querySelector("a[target=_blank]").href = url;
            viewer.querySelector("a[data-no-loader]").href = button.dataset.download || url;
        }
        drawer.hidden = false;
        backdrop.hidden = false;
        requestAnimationFrame(() => drawer.classList.add("is-open"));
        if (viewer && window.SGSIPdf) window.SGSIPdf.mount(viewer, url);
        document.body.classList.add("pdf-open");
    }
    function closePdf() {
        drawer.classList.remove("is-open");
        drawer.hidden = true;
        backdrop.hidden = true;
        document.body.classList.remove("pdf-open");
        opener?.focus();
    }
    document.addEventListener("click", (event) => {
        const button = event.target.closest("[data-open-pdf]");
        if (button) { event.preventDefault(); openPdf(button); }
    });
    drawer?.querySelector("[data-pdf-close]")?.addEventListener("click", closePdf);
    backdrop?.addEventListener("click", closePdf);
    document.addEventListener("keydown", (event) => { if (event.key === "Escape" && drawer && !drawer.hidden) closePdf(); });
});
