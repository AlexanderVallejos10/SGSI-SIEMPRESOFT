document.addEventListener("DOMContentLoaded", () => {
    const canvas = document.querySelector("[data-process-canvas]");
    const stage = document.querySelector("[data-process-stage]");
    const svg = document.querySelector("[data-process-lines]");
    const detail = document.querySelector("[data-process-detail]");
    const saveButton = document.querySelector("[data-save-layout]");
    const saveState = document.querySelector("[data-map-save-state]");
    const loader = document.querySelector("[data-map-loader]");

    const processDataElement = document.getElementById("process-data");
    const relationDataElement = document.getElementById("relation-data");

    const processData = processDataElement
        ? JSON.parse(processDataElement.textContent)
        : {};

    const relations = relationDataElement
        ? JSON.parse(relationDataElement.textContent)
        : [];

    const nodes = Array.from(document.querySelectorAll(".process-node"));
    const pendingMoves = new Map();

    let zoom = 1;
    let dragging = null;

    function categoryForY(y) {
        if (y < 150) return "strategic";
        if (y < 500) return "operational";
        return "support";
    }

    function clamp(value, min, max) {
        return Math.max(min, Math.min(max, value));
    }

    function nodeCenter(node) {
        return {
            x: parseFloat(node.style.left) + (node.offsetWidth / 2),
            y: parseFloat(node.style.top) + (node.offsetHeight / 2),
        };
    }

    function removeDynamicLines() {
        svg?.querySelectorAll("[data-dynamic-line]").forEach((item) => {
            item.remove();
        });
    }

    function drawRelation(sourceNode, targetNode, relation) {
        if (!sourceNode || !targetNode || !svg) return;

        const source = nodeCenter(sourceNode);
        const target = nodeCenter(targetNode);
        const ns = "http://www.w3.org/2000/svg";
        const path = document.createElementNS(ns, "path");

        const dx = target.x - source.x;
        const dy = target.y - source.y;
        let d;

        if (Math.abs(dx) > Math.abs(dy)) {
            const midX = source.x + dx / 2;
            d = [
                `M ${source.x} ${source.y}`,
                `L ${midX} ${source.y}`,
                `L ${midX} ${target.y}`,
                `L ${target.x} ${target.y}`,
            ].join(" ");
        } else {
            const midY = source.y + dy / 2;
            d = [
                `M ${source.x} ${source.y}`,
                `L ${source.x} ${midY}`,
                `L ${target.x} ${midY}`,
                `L ${target.x} ${target.y}`,
            ].join(" ");
        }

        path.setAttribute("d", d);
        path.dataset.dynamicLine = "1";
        path.dataset.source = relation.source;
        path.dataset.target = relation.target;
        path.classList.add(`relation-${relation.type}`);
        svg.appendChild(path);
    }

    function redrawLines() {
        removeDynamicLines();

        relations.forEach((relation) => {
            const source = document.querySelector(
                `[data-process-id="${CSS.escape(relation.source)}"]`
            );
            const target = document.querySelector(
                `[data-process-id="${CSS.escape(relation.target)}"]`
            );
            drawRelation(source, target, relation);
        });
    }

    function escapeHtml(value) {
        const div = document.createElement("div");
        div.textContent = String(value ?? "");
        return div.innerHTML;
    }

    function renderDetail(processId) {
        const data = processData[processId];

        if (!data || !detail) return;

        nodes.forEach((node) => {
            node.classList.toggle(
                "selected",
                node.dataset.processId === processId
            );
        });

        const documentRows = data.documents.length
            ? data.documents.map((item) => `
                <a href="${item.url}">
                    <b>${escapeHtml(item.code)}</b>
                    ${escapeHtml(item.title)}
                </a>
            `).join("")
            : "<div>Sin documentos vinculados.</div>";

        const relationRows = [
            ...data.incoming.map((item) => `
                <div>
                    Entrante desde <b>${escapeHtml(item.process)}</b>
                </div>
            `),
            ...data.outgoing.map((item) => `
                <div>
                    Saliente hacia <b>${escapeHtml(item.process)}</b>
                </div>
            `),
        ].join("");

        const areas = data.areas.length
            ? data.areas.join(", ")
            : "Sin áreas adicionales";

        const participants = data.participants.length
            ? data.participants.join(", ")
            : "Sin participantes directos";

        detail.innerHTML = `
            <div class="process-detail-content">
                <header>
                    <h2>${escapeHtml(data.name)}</h2>
                    <span>
                        ${escapeHtml(data.category_name)}
                        ${data.is_in_scope ? " · dentro del alcance" : " · fuera del alcance"}
                    </span>
                </header>

                <div class="process-detail-actions">
                    <a class="outline-btn" href="${data.edit_url}">
                        Editar proceso
                    </a>
                    <a class="outline-btn" href="${data.detail_url}">
                        Abrir ficha
                    </a>
                </div>

                <section class="process-detail-section">
                    <h3>Responsabilidad</h3>
                    <dl>
                        <div>
                            <dt>Puesto</dt>
                            <dd>${escapeHtml(data.owner_position || "Pendiente")}</dd>
                        </div>
                        <div>
                            <dt>Área</dt>
                            <dd>${escapeHtml(data.responsible_area || "Pendiente")}</dd>
                        </div>
                        <div>
                            <dt>Responsable actual</dt>
                            <dd>
                                ${
                                    data.owner_user
                                    ? `<a href="${data.owner_user.url}">${escapeHtml(data.owner_user.name)}</a>`
                                    : "Pendiente"
                                }
                            </dd>
                        </div>
                    </dl>
                </section>

                <section class="process-detail-section">
                    <h3>Descripción</h3>
                    <p>${escapeHtml(data.description || "Sin descripción.")}</p>
                </section>

                <section class="process-detail-section">
                    <h3>Involucrados</h3>
                    <p><b>Áreas:</b> ${escapeHtml(areas)}</p>
                    <p><b>Usuarios:</b> ${escapeHtml(participants)}</p>
                </section>

                <section class="process-detail-section">
                    <h3>Documentos vinculados</h3>
                    <div class="detail-links">${documentRows}</div>
                </section>

                <section class="process-detail-section">
                    <h3>Relaciones SGSI</h3>
                    <div class="detail-counts">
                        <div><strong>${data.control_count}</strong><span>controles</span></div>
                        <div><a href="${data.risk_url}"><strong>${data.risk_count}</strong><span>Abrir matriz de riesgos</span></a></div>
                        <div><strong>${data.asset_count}</strong><span>activos</span></div>
                    </div>
                </section>

                <section class="process-detail-section">
                    <h3>Relaciones del mapa</h3>
                    <div class="detail-links">
                        ${relationRows || "<div>Sin relaciones registradas.</div>"}
                    </div>
                </section>
            </div>
        `;
    }

    function setDirty() {
        if (saveState) {
            saveState.textContent = "Cambios pendientes";
            saveState.style.color = "#a16d25";
        }
    }

    function pointerDown(event) {
        const node = event.currentTarget;

        if (!event.target.closest(".drag-handle")) {
            return;
        }

        event.preventDefault();

        const rect = stage.getBoundingClientRect();

        dragging = {
            node,
            offsetX:
                (event.clientX - rect.left) / zoom
                - parseFloat(node.style.left),
            offsetY:
                (event.clientY - rect.top) / zoom
                - parseFloat(node.style.top),
        };

        node.classList.add("dragging");
        node.setPointerCapture(event.pointerId);
    }

    function pointerMove(event) {
        if (!dragging) return;

        const rect = stage.getBoundingClientRect();

        let x =
            (event.clientX - rect.left) / zoom
            - dragging.offsetX;

        let y =
            (event.clientY - rect.top) / zoom
            - dragging.offsetY;

        x = clamp(Math.round(x), 0, 1035);
        y = clamp(Math.round(y), 45, 635);

        dragging.node.style.left = `${x}px`;
        dragging.node.style.top = `${y}px`;

        const category = categoryForY(y);
        dragging.node.dataset.category = category;

        pendingMoves.set(
            dragging.node.dataset.processId,
            {
                id: dragging.node.dataset.processId,
                x,
                y,
                category,
            }
        );

        setDirty();
        redrawLines();
    }

    function pointerUp() {
        if (!dragging) return;
        dragging.node.classList.remove("dragging");
        dragging = null;
    }

    nodes.forEach((node) => {
        node.addEventListener("click", () => {
            renderDetail(node.dataset.processId);
        });

        node.addEventListener("pointerdown", pointerDown);
        node.addEventListener("pointermove", pointerMove);
        node.addEventListener("pointerup", pointerUp);
        node.addEventListener("pointercancel", pointerUp);
    });

    redrawLines();

    if (nodes.length) {
        renderDetail(nodes[0].dataset.processId);
    }

    if (saveButton) {
        saveButton.addEventListener("click", async () => {
            const moves = Array.from(pendingMoves.values());

            if (!moves.length) {
                if (saveState) {
                    saveState.textContent = "No hay cambios por guardar";
                }
                return;
            }

            saveButton.disabled = true;
            saveButton.textContent = "Guardando...";

            try {
                const response = await fetch(
                    "/procesos/mapa/guardar/",
                    {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                            "X-CSRFToken": getCookie("csrftoken"),
                        },
                        body: JSON.stringify({ moves }),
                    }
                );

                const result = await response.json();

                if (!response.ok || !result.ok) {
                    throw new Error(
                        result.error || "No se pudo guardar."
                    );
                }

                pendingMoves.clear();

                if (saveState) {
                    saveState.textContent =
                        `${result.updated} cambio(s) guardado(s)`;
                    saveState.style.color = "#3f7756";
                }
            } catch (error) {
                if (saveState) {
                    saveState.textContent = error.message;
                    saveState.style.color = "#a94747";
                }
            } finally {
                saveButton.disabled = false;
                saveButton.textContent = "Guardar cambios";
            }
        });
    }

    function getCookie(name) {
        const cookies = document.cookie
            .split(";")
            .map((item) => item.trim());

        const value = cookies.find((item) =>
            item.startsWith(`${name}=`)
        );

        return value
            ? decodeURIComponent(value.split("=")[1])
            : "";
    }

    function applyZoom() {
        if (!stage || !canvas) return;
        stage.style.transform = "none";
        stage.style.zoom = zoom;
        document.querySelector("[data-zoom-label]").textContent = `${Math.round(zoom*100)}%`;
        canvas.style.height = `${Math.min(780, 760*zoom+30)}px`;
    }
    function fitMap() {
        if (!canvas) return;
        zoom = Math.min(1, Math.max(.25, (canvas.clientWidth-24)/1320));
        applyZoom();
    }
    document.querySelector("[data-fit-map]")?.addEventListener("click", fitMap);
    document.querySelector("[data-zoom-in]")?.addEventListener("click",()=>{zoom=Math.min(1.5,zoom+.1);applyZoom();});
    document.querySelector("[data-zoom-out]")?.addEventListener("click",()=>{zoom=Math.max(.25,zoom-.1);applyZoom();});
    if(canvas) new ResizeObserver(fitMap).observe(canvas);
    fitMap();
    window.requestAnimationFrame(() => loader?.classList.add("is-ready"));
    window.addEventListener("beforeunload",event=>{if(pendingMoves.size){event.preventDefault();event.returnValue="";}});

    document.querySelector("[data-fullscreen]")?.addEventListener(
        "click",
        async () => {
            if (canvas && canvas.requestFullscreen) {
                await canvas.requestFullscreen();
            }
        }
    );

    const relationDialog = document.querySelector(
        "[data-relation-dialog]"
    );

    document.querySelector(
        "[data-open-relation-dialog]"
    )?.addEventListener(
        "click",
        () => relationDialog?.showModal()
    );

    document.querySelectorAll(
        "[data-close-relation-dialog]"
    ).forEach((button) => {
        button.addEventListener(
            "click",
            () => relationDialog?.close()
        );
    });
});
