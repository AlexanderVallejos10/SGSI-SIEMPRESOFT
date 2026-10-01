// Presencia y notificaciones en tiempo real: una consulta cada 25 s a /api/pulso/.
(() => {
  "use strict";
  const cfg = document.querySelector("[data-live-config]");
  if (!cfg) return;
  const PULSE = cfg.dataset.pulse, LOGIN = cfg.dataset.login, READ = cfg.dataset.read;
  const EVERY = 25000, MAX_WAIT = 180000;
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const face = (p, cls = "") => (p.photo
    ? `<span class="ac-avatar has-photo ${cls}" title="${esc(p.name)}"><img src="${esc(p.photo)}" alt="" loading="lazy"></span>`
    : `<span class="ac-avatar ${cls}" title="${esc(p.name)}">${esc(p.initials)}</span>`);
  const csrf = () => (document.cookie.split(";").map((c) => c.trim()).find((c) => c.startsWith("csrftoken=")) || "").split("=")[1] || "";
  let lastId = 0, first = true, wait = EVERY, timer = null;

  // ---------------------------------------------------------------- menús desplegables de la barra
  document.addEventListener("click", (ev) => {
    const toggle = ev.target.closest("[data-pop-toggle]");
    document.querySelectorAll("[data-pop]").forEach((pop) => {
      const menu = pop.querySelector("[data-pop-menu]"), btn = pop.querySelector("[data-pop-toggle]");
      const open = toggle && pop.contains(toggle) ? menu.hidden : false;
      if (!pop.contains(ev.target) || toggle) { menu.hidden = !open; btn.setAttribute("aria-expanded", String(open)); }
    });
  });
  document.addEventListener("keydown", (ev) => {
    if (ev.key !== "Escape") return;
    document.querySelectorAll("[data-pop-menu]").forEach((m) => { m.hidden = true; });
    document.querySelectorAll("[data-pop-toggle]").forEach((b) => b.setAttribute("aria-expanded", "false"));
  });

  // ---------------------------------------------------------------- avisos emergentes
  function toast(n) {
    const box = document.querySelector("[data-live-toasts]");
    box.querySelectorAll(".tb-toast").forEach((old) => old.remove());
    const el = document.createElement(n.url ? "a" : "div");
    el.className = "tb-toast";
    if (n.url) el.href = n.url;
    el.innerHTML = `<b>${esc(n.title)}</b>${n.body ? `<span>${esc(n.body)}</span>` : ""}`;
    if (n.id) el.addEventListener("click", () => markRead(n.id));
    box.appendChild(el);
    if (!reduce) el.animate([{ opacity: 0, transform: "translateY(8px)" }, { opacity: 1, transform: "none" }], { duration: 220, easing: "ease-out" });
    setTimeout(() => {
      if (reduce) { el.remove(); return; }
      el.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 200 }).onfinish = () => el.remove();
    }, 6500);
  }

  function markRead(id) {
    return fetch(READ.replace("/0/", `/${id}/`), { method: "POST", credentials: "same-origin", headers: { "X-CSRFToken": decodeURIComponent(csrf()) } }).catch(() => {});
  }

  // ---------------------------------------------------------------- pintar
  function paint(data) {
    const people = data.online || [];
    const others = people.filter((p) => !p.me);
    document.querySelectorAll("[data-online-label]").forEach((el) => { el.textContent = `${people.length} conectado${people.length === 1 ? "" : "s"}`; });
    document.querySelectorAll("[data-online-count]").forEach((el) => { el.textContent = people.length || ""; });
    document.querySelectorAll("[data-online-faces]").forEach((el) => {
      el.innerHTML = people.slice(0, 3).map((p) => face(p)).join("");
    });
    document.querySelectorAll("[data-online-list]").forEach((ul) => {
      ul.innerHTML = people.length ? people.map((p) => `<li><span class="ac-person"><span class="ac-presence is-on">${face(p)}</span><span><b>${esc(p.name)}${p.me ? " (usted)" : ""}</b><small>${esc(p.position || "")}${p.position ? ", " : ""}hace ${esc(p.since)}</small></span></span></li>`).join("")
        : '<li class="tb-empty">No hay nadie conectado.</li>';
    });
    document.querySelectorAll("[data-unread]").forEach((b) => { b.textContent = data.unread > 99 ? "99+" : data.unread; b.hidden = !data.unread; });
    const notes = data.notifications || [];
    document.querySelectorAll("[data-notif-list]").forEach((ul) => {
      if (first || notes.length) {
        const unread = notes.filter((n) => !n.read);
        ul.innerHTML = unread.length ? unread.map((n) => `<li><a href="${esc(n.url || "#")}" data-read-id="${n.id}"><b>${esc(n.title)}</b>${n.body ? `<small>${esc(n.body)}</small>` : ""}<time>${new Date(n.created).toLocaleString("es-PE", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })}</time></a></li>`).join("")
          : '<li class="tb-empty">Sin notificaciones nuevas.</li>';
      }
    });
    if (!first) {
      const nuevas = notes.filter((n) => n.id > lastId && !n.read);
      if (nuevas.length === 1) toast(nuevas[0]);
      else if (nuevas.length > 1) toast({ title: `${nuevas.length} notificaciones nuevas`, body: nuevas[0].title, url: cfg.dataset.list || "" });
    }
    lastId = Math.max(lastId, data.last_id || 0);
    if ("pending_requests" in data) {
      document.querySelectorAll("[data-requests-badge]").forEach((b) => { b.textContent = data.pending_requests; b.hidden = !data.pending_requests; });
    }
    first = false;
  }

  document.addEventListener("click", (ev) => {
    const a = ev.target.closest("[data-read-id]");
    if (a) markRead(a.dataset.readId);
  });

  // ---------------------------------------------------------------- consulta periódica
  async function pulse() {
    clearTimeout(timer);
    try {
      const url = new URL(PULSE, window.location.origin);
      if (lastId) url.searchParams.set("after", lastId);
      const res = await fetch(url, { credentials: "same-origin", headers: { Accept: "application/json" } });
      if (res.status === 401 || res.redirected) {
        window.location.href = `${LOGIN}?next=${encodeURIComponent(window.location.pathname + window.location.search)}`;
        return;
      }
      if (!res.ok) throw new Error(String(res.status));
      paint(await res.json());
      wait = EVERY;
    } catch (e) {
      wait = Math.min(wait * 2, MAX_WAIT); // si el servidor no responde, reintenta cada vez más espaciado
    }
    if (!document.hidden) timer = setTimeout(pulse, wait);
  }
  document.addEventListener("visibilitychange", () => { if (!document.hidden) pulse(); else clearTimeout(timer); });
  document.addEventListener("DOMContentLoaded", pulse);
  if (document.readyState !== "loading") pulse();
})();
