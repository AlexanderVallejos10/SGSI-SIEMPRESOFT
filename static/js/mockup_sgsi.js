
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".clause-menu").forEach(menu => {
    menu.addEventListener("toggle", () => {
      if (!menu.open) return;
      document.querySelectorAll(".clause-menu").forEach(other => {
        if (other !== menu) other.open = false;
      });
    });
  });
});
