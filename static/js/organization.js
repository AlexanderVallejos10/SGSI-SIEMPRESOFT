document.addEventListener("DOMContentLoaded", () => {
    let zoom = 1;
    const stage = document.querySelector("[data-org-stage]");
    const label = document.querySelector("[data-zoom-label]");

    function applyZoom() {
        if (!stage) return;
        stage.style.transform = `scale(${zoom})`;
        if (label) {
            label.textContent = `${Math.round(zoom * 100)}%`;
        }
    }

    document.querySelector("[data-zoom-in]")?.addEventListener("click", () => {
        zoom = Math.min(1.5, zoom + 0.1);
        applyZoom();
    });

    document.querySelector("[data-zoom-out]")?.addEventListener("click", () => {
        zoom = Math.max(0.55, zoom - 0.1);
        applyZoom();
    });

    document.querySelector("[data-zoom-reset]")?.addEventListener("click", () => {
        zoom = 1;
        applyZoom();

        const canvas = document.querySelector(".org-canvas");
        if (canvas) {
            canvas.scrollLeft = Math.max(
                0,
                (canvas.scrollWidth - canvas.clientWidth) / 2,
            );
        }
    });

    document.querySelectorAll("[data-node-menu-button]").forEach((button) => {
        button.addEventListener("click", (event) => {
            event.stopPropagation();

            document.querySelectorAll(".node-menu.open").forEach((menu) => {
                if (menu !== button.closest(".node-menu")) {
                    menu.classList.remove("open");
                }
            });

            button.closest(".node-menu")?.classList.toggle("open");
        });
    });

    document.addEventListener("click", () => {
        document.querySelectorAll(".node-menu.open").forEach((menu) => {
            menu.classList.remove("open");
        });
    });

    document.querySelectorAll("[data-node-menu]").forEach((menu) => {
        menu.addEventListener("click", (event) => {
            event.stopPropagation();
        });
    });

    document.querySelectorAll("[data-collapse-branch]").forEach((button) => {
        button.addEventListener("click", () => {
            const item = button.closest(".org-node-item");
            if (!item) return;

            const collapsed = item.classList.toggle("branch-collapsed");
            button.textContent = collapsed ? "+" : "−";
            button.setAttribute("aria-expanded", collapsed ? "false" : "true");
        });
    });

    window.setTimeout(() => {
        const canvas = document.querySelector(".org-canvas");
        if (canvas) {
            canvas.scrollLeft = Math.max(
                0,
                (canvas.scrollWidth - canvas.clientWidth) / 2,
            );
        }
    }, 100);
});
