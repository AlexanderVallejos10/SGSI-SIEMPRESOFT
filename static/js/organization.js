document.addEventListener("DOMContentLoaded", () => {
    let zoom = 1;
    const stage = document.querySelector("[data-org-stage]");
    const label = document.querySelector("[data-zoom-label]");

    function applyZoom() {
        if (!stage) return;
        stage.style.transform = "none";
        stage.style.zoom = zoom;
        if (label) {
            label.textContent = `${Math.round(zoom * 100)}%`;
        }
    }

    document.querySelector("[data-zoom-in]")?.addEventListener("click", () => {
        zoom = Math.min(1.5, zoom + 0.1);
        applyZoom();
    });

    document.querySelector("[data-zoom-out]")?.addEventListener("click", () => {
        zoom = Math.max(0.25, zoom - 0.1);
        applyZoom();
    });

    document.querySelector("[data-zoom-reset]")?.addEventListener("click", () => {
        zoom = Math.min(1, document.querySelector(".org-canvas").clientWidth / stage.scrollWidth);
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

    function search() {
        const q = document.querySelector('[data-org-search]').value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
        const area = document.querySelector('[data-org-area]').value;
        let count = 0, first = null;
        document.querySelectorAll('.org-node').forEach(node=>{
            const match = (!q || node.innerText.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().includes(q)) && (!area || node.dataset.area===area);
            node.classList.toggle('org-muted', !match);node.classList.toggle('org-match', match && Boolean(q||area));
            if(match){count++;first ||= node;}
        });
        document.querySelector('[data-org-result]').textContent = `${count} puestos`;
        if(first && (q||area)){
            let parent=first.parentElement;
            while(parent){parent.classList.remove('branch-collapsed');const toggle=parent.querySelector(':scope > article > [data-collapse-branch]');if(toggle){toggle.textContent='−';toggle.setAttribute('aria-expanded','true');}parent=parent.parentElement.closest('.org-node-item');}
            first.scrollIntoView({block:'nearest',inline:'center'});
        }
    }
    document.querySelector('[data-org-search]')?.addEventListener('input',search);
    document.querySelector('[data-org-area]')?.addEventListener('change',search);
    window.setTimeout(() => {
        if(stage){zoom=Math.min(.85,Math.max(.25,document.querySelector('.org-canvas').clientWidth/stage.scrollWidth));applyZoom();}
        const canvas = document.querySelector(".org-canvas");
        if (canvas) {
            canvas.scrollLeft = Math.max(
                0,
                (canvas.scrollWidth - canvas.clientWidth) / 2,
            );
        }
    }, 100);
});
