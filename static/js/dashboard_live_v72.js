document.addEventListener("DOMContentLoaded", () => {
  const tabs = Array.from(document.querySelectorAll("[data-dashboard-tab]"));
  const panels = Array.from(document.querySelectorAll("[data-dashboard-panel]"));

  function activate(name, updateUrl = true) {
    tabs.forEach((tab) => tab.classList.toggle("active", tab.dataset.dashboardTab === name));
    panels.forEach((panel) => panel.classList.toggle("active", panel.dataset.dashboardPanel === name));
    if (updateUrl) {
      const url = new URL(window.location.href);
      url.searchParams.set("tab", name);
      window.history.replaceState({}, "", url);
    }
  }

  tabs.forEach((tab) => tab.addEventListener("click", () => activate(tab.dataset.dashboardTab)));
  document.querySelectorAll("[data-open-tab]").forEach((button) => {
    button.addEventListener("click", () => activate(button.dataset.openTab));
  });

  function getCookie(name) {
    const value = document.cookie.split(";").map((item) => item.trim()).find((item) => item.startsWith(`${name}=`));
    return value ? decodeURIComponent(value.split("=")[1]) : "";
  }

  document.querySelectorAll("[data-toggle-url]").forEach((button) => {
    button.addEventListener("click", async () => {
      button.disabled = true;
      try {
        const response = await fetch(button.dataset.toggleUrl, {
          method: "POST",
          headers: {"X-CSRFToken": getCookie("csrftoken")},
        });
        const payload = await response.json();
        if (!response.ok || !payload.ok) throw new Error("No se pudo actualizar la matriz.");
        const url = new URL(window.location.href);
        const panel = button.closest("[data-dashboard-panel]");
        if (panel) url.searchParams.set("tab", panel.dataset.dashboardPanel);
        window.location.assign(url.toString());
      } catch (error) {
        window.alert(error.message);
        button.disabled = false;
      }
    });
  });
});
