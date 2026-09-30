// Microinteracciones y personalización comunes a todos los módulos.
(() => {
  "use strict";
  const doc = document.documentElement;
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* sin almacenamiento */ } },
  };

  // ---------------------------------------------------------------- acento y densidad
  function syncControls() {
    document.querySelectorAll("[data-accent-value]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.accentValue === (doc.dataset.accent || "green"))));
    document.querySelectorAll("[data-density-toggle]").forEach((b) => b.setAttribute("aria-pressed", String(doc.dataset.density === "compact")));
  }
  document.addEventListener("click", (ev) => {
    const accent = ev.target.closest("[data-accent-value]");
    if (accent) {
      doc.dataset.accent = accent.dataset.accentValue;
      store.set("sgsi-accent", accent.dataset.accentValue);
      syncControls();
    }
    if (ev.target.closest("[data-density-toggle]")) {
      doc.dataset.density = doc.dataset.density === "compact" ? "comfortable" : "compact";
      store.set("sgsi-density", doc.dataset.density);
      syncControls();
      document.dispatchEvent(new CustomEvent("sd:density"));
    }
  });

  // ---------------------------------------------------------------- mensajes del sistema
  function messages() {
    document.querySelectorAll(".system-message").forEach((msg, i) => {
      const close = document.createElement("button");
      close.type = "button"; close.className = "sys-close"; close.setAttribute("aria-label", "Cerrar"); close.textContent = "×";
      msg.appendChild(close);
      const hide = () => {
        if (reduce) { msg.remove(); return; }
        const a = msg.animate([{ opacity: 1, transform: "none" }, { opacity: 0, transform: "translateY(-6px)" }], { duration: 220 });
        a.onfinish = () => msg.remove();
      };
      close.addEventListener("click", hide);
      if (!/error|no se pudo|no se encontr/i.test(msg.textContent)) setTimeout(hide, 7000 + i * 800); // los errores se quedan
    });
  }

  document.addEventListener("DOMContentLoaded", () => { syncControls(); messages(); });
})();
