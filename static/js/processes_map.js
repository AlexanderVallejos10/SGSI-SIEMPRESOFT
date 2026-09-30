// Mapa de procesos SIEMPRESOFT.
// Las franjas (estratégicos, operativos, apoyo) crecen según los procesos que contienen,
// el marco del alcance se calcula con los procesos dentro del alcance, y las partes
// interesadas (Cliente / PSE, Cliente / PSE / SUNAT) son columnas que envían y reciben flujos.
document.addEventListener("DOMContentLoaded", () => {
    "use strict";

    const canvas = document.querySelector("[data-process-canvas]");
    const sizer = document.querySelector("[data-map-sizer]");
    const stage = document.querySelector("[data-process-stage]");
    const svg = document.querySelector("[data-process-lines]");
    const linksLayer = svg?.querySelector("[data-map-links]");
    const blocksLayer = svg?.querySelector("[data-map-blocks]");
    const box = stage?.querySelector("[data-map-box]");
    const lanesLayer = stage?.querySelector("[data-map-lanes]");
    const scopeFrame = stage?.querySelector("[data-map-scope]");
    const legend = stage?.querySelector("[data-map-legend]");
    const detail = document.querySelector("[data-process-detail]");
    const saveButton = document.querySelector("[data-save-layout]");
    const saveState = document.querySelector("[data-map-save-state]");
    const loader = document.querySelector("[data-map-loader]");
    if (!stage || !svg) return;

    const processData = JSON.parse(document.getElementById("process-data")?.textContent || "{}");
    const relations = JSON.parse(document.getElementById("relation-data")?.textContent || "[]");
    const nodes = Array.from(stage.querySelectorAll(".process-node"));
    const byId = new Map(nodes.map((node) => [node.dataset.processId, node]));

    const LANES = [
        { kind: "strategic", label: "PROCESOS ESTRATÉGICOS", min: 118, pad: 50 },
        { kind: "operational", label: "PROCESOS OPERATIVOS", min: 230, pad: 58 },
        { kind: "support", label: "PROCESOS DE APOYO", min: 140, pad: 26 },
    ];
    const LANE_NAMES = { strategic: "Procesos estratégicos", operational: "Procesos operativos", support: "Procesos de apoyo" };
    const NODE_W = 180;
    const INNER_W = 1120;
    const PARTY_W = 48;
    const PARTY_GAP = 14;
    const MARGIN = 14;
    const TOP = 52;
    const NS = "http://www.w3.org/2000/svg";

    const pendingMoves = new Map();
    const originalKind = new Map(nodes.map((node) => [node.dataset.processId, node.dataset.kind]));
    let geometry = null;
    let scale = 1;
    let dragging = null;

    const isParty = (node) => node.dataset.kind === "input" || node.dataset.kind === "output";

    // ---------- Distribución ----------
    function layout() {
        const inputs = nodes.filter((n) => n.dataset.kind === "input");
        const outputs = nodes.filter((n) => n.dataset.kind === "output");
        const boxLeft = MARGIN + inputs.length * (PARTY_W + PARTY_GAP) + (inputs.length ? 4 : 0);
        const boxTop = TOP;

        // Coloca primero los procesos para medir su alto real.
        nodes.filter((n) => !isParty(n)).forEach((node) => {
            node.style.width = `${NODE_W}px`;
        });

        let laneTop = boxTop;
        const lanes = LANES.map((lane) => {
            const members = nodes.filter((n) => n.dataset.kind === lane.kind);
            const bottom = members.reduce((max, n) => Math.max(max, Number(n.dataset.y) + n.offsetHeight), 0);
            const height = Math.max(lane.min, bottom + lane.pad);
            const rect = { ...lane, top: laneTop, height, members };
            members.forEach((node) => {
                const x = Math.min(Number(node.dataset.x), INNER_W - NODE_W - 10);
                node.style.left = `${boxLeft + Math.max(0, x)}px`;
                node.style.top = `${laneTop + Number(node.dataset.y)}px`;
            });
            laneTop += height;
            return rect;
        });
        const boxHeight = laneTop - boxTop;

        // Partes interesadas: columnas a lo alto del mapa.
        inputs.forEach((node, i) => {
            Object.assign(node.style, {
                left: `${boxLeft - 4 - (i + 1) * (PARTY_W + PARTY_GAP) + PARTY_GAP}px`,
                top: `${boxTop}px`, width: `${PARTY_W}px`, height: `${boxHeight}px`,
            });
        });
        outputs.forEach((node, i) => {
            Object.assign(node.style, {
                left: `${boxLeft + INNER_W + 4 + PARTY_GAP + i * (PARTY_W + PARTY_GAP)}px`,
                top: `${boxTop}px`, width: `${PARTY_W}px`, height: `${boxHeight}px`,
            });
        });

        const width = boxLeft + INNER_W + (outputs.length ? 4 + outputs.length * (PARTY_W + PARTY_GAP) : 0) + MARGIN;
        const height = boxTop + boxHeight + 64;

        Object.assign(box.style, { left: `${boxLeft}px`, top: `${boxTop}px`, width: `${INNER_W}px`, height: `${boxHeight}px` });
        lanesLayer.innerHTML = lanes.map((lane, i) => `
            <div class="map-v2-lane" data-lane="${lane.kind}" style="left:${boxLeft}px;top:${lane.top}px;width:${INNER_W}px;height:${lane.height}px">
                ${i ? '<i class="map-v2-rule"></i>' : ""}
                <span class="map-v2-tab">${lane.label}</span>
            </div>`).join("");

        // Marco del alcance: rodea los procesos marcados dentro del alcance.
        const scoped = nodes.filter((n) => !isParty(n) && n.dataset.scope === "1");
        let frame = null;
        if (scoped.length) {
            const r = scoped.map(rectOf);
            frame = {
                left: Math.max(boxLeft + 8, Math.min(...r.map((x) => x.x)) - 30),
                top: Math.min(...r.map((x) => x.y)) - 28,
                right: Math.min(boxLeft + INNER_W - 8, Math.max(...r.map((x) => x.x + x.w)) + 30),
                bottom: Math.max(...r.map((x) => x.y + x.h)) + 24,
            };
            Object.assign(scopeFrame.style, {
                left: `${frame.left}px`, top: `${frame.top}px`,
                width: `${frame.right - frame.left}px`, height: `${frame.bottom - frame.top}px`,
            });
            scopeFrame.hidden = false;
        } else {
            scopeFrame.hidden = true;
        }

        Object.assign(stage.style, { width: `${width}px`, height: `${height}px` });
        svg.setAttribute("width", width);
        svg.setAttribute("height", height);
        svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
        Object.assign(legend.style, { left: `${boxLeft}px`, top: `${boxTop + boxHeight + 22}px`, width: `${INNER_W}px` });

        geometry = { boxLeft, boxTop, boxHeight, width, height, lanes, frame };
        drawBlocks();
        drawLinks();
        applyScale();
    }

    function rectOf(node) {
        const x = parseFloat(node.style.left);
        const y = parseFloat(node.style.top);
        const w = node.offsetWidth;
        const h = node.offsetHeight;
        return { x, y, w, h, cx: x + w / 2, cy: y + h / 2, kind: node.dataset.kind };
    }

    // Flechas gruesas: la dirección orienta a la operación y el apoyo la sostiene.
    function drawBlocks() {
        blocksLayer.innerHTML = "";
        const { lanes, frame, boxLeft } = geometry;
        const centerX = frame ? (frame.left + frame.right) / 2 : boxLeft + INNER_W / 2;
        const [strategic, operational, support] = lanes;
        const block = (x, yTip, yTail, up) => {
            const w = 34, head = 16, shaft = 17;
            const dir = up ? -1 : 1;
            const neck = yTip - dir * head;
            const points = [
                [x - shaft / 2, yTail], [x + shaft / 2, yTail], [x + shaft / 2, neck],
                [x + w / 2, neck], [x, yTip], [x - w / 2, neck], [x - shaft / 2, neck],
            ].map((p) => p.join(",")).join(" ");
            const poly = document.createElementNS(NS, "polygon");
            poly.setAttribute("points", points);
            poly.setAttribute("class", "map-v2-block");
            blocksLayer.appendChild(poly);
        };
        if (strategic.members.length && operational.members.length) {
            const bottom = strategic.top + strategic.height;
            block(centerX, bottom - 6, bottom - 42, false);
        }
        if (support.members.length && operational.members.length) {
            const bottom = operational.top + operational.height;
            block(centerX, bottom - 44, bottom - 8, true);
        }
    }

    // ---------- Relaciones ----------
    // ¿Un tramo horizontal atraviesa alguna caja que no sea origen ni destino?
    function blocked(y, x1, x2, skip) {
        const lo = Math.min(x1, x2), hi = Math.max(x1, x2);
        return nodes.some((n) => {
            if (isParty(n) || skip.includes(n)) return false;
            const r = rectOf(n);
            return y > r.y - 4 && y < r.y + r.h + 4 && r.x + r.w > lo && r.x < hi;
        });
    }

    // Flechas desde o hacia una parte interesada: recta si el camino está libre;
    // si no, bordea la fila por arriba o por abajo y entra por el borde de la caja.
    function partyRoute(edgeX, proc, procNode, entering) {
        const side = edgeX < proc.x ? proc.x : proc.x + proc.w;
        if (!blocked(proc.cy, edgeX, side, [procNode])) return entering ? [[edgeX, proc.cy], [side, proc.cy]] : [[side, proc.cy], [edgeX, proc.cy]];
        for (const [y, portY] of [[proc.y - 18, proc.y], [proc.y + proc.h + 18, proc.y + proc.h]]) {
            if (!blocked(y, edgeX, proc.cx, [procNode])) {
                const pts = [[edgeX, y], [proc.cx, y], [proc.cx, portY]];
                return entering ? pts : pts.reverse();
            }
        }
        return entering ? [[edgeX, proc.cy], [side, proc.cy]] : [[side, proc.cy], [edgeX, proc.cy]];
    }

    function route(a, b, aNode, bNode) {
        if (a.kind === "input") return partyRoute(a.x + a.w, b, bNode, true);
        if (b.kind === "output") return partyRoute(b.x, a, aNode, false);
        if (a.kind === "output") return partyRoute(a.x, b, bNode, true);
        if (b.kind === "input") return partyRoute(b.x + b.w, a, aNode, false);

        const gapX = Math.max(b.x - (a.x + a.w), a.x - (b.x + b.w));
        const gapY = Math.max(b.y - (a.y + a.h), a.y - (b.y + b.h));
        if (gapX >= gapY) {
            const right = b.cx > a.cx;
            const sx = right ? a.x + a.w : a.x;
            const ex = right ? b.x : b.x + b.w;
            if (Math.abs(a.cy - b.cy) < 8) {
                const y = (a.cy + b.cy) / 2;
                return [[sx, y], [ex, y]];
            }
            const mid = (sx + ex) / 2;
            return [[sx, a.cy], [mid, a.cy], [mid, b.cy], [ex, b.cy]];
        }
        const down = b.cy > a.cy;
        const sy = down ? a.y + a.h : a.y;
        const ey = down ? b.y : b.y + b.h;
        if (Math.abs(a.cx - b.cx) < 8) {
            const x = (a.cx + b.cx) / 2;
            return [[x, sy], [x, ey]];
        }
        const mid = (sy + ey) / 2;
        return [[a.cx, sy], [a.cx, mid], [b.cx, mid], [b.cx, ey]];
    }

    function drawLinks() {
        linksLayer.innerHTML = "";
        const seen = new Set();
        relations.forEach((relation) => {
            const source = byId.get(relation.source);
            const target = byId.get(relation.target);
            if (!source || !target) return;
            const pairKey = [relation.source, relation.target].sort().join("|") + relation.type;
            if (seen.has(pairKey)) return;
            const reverse = relations.some((r) => r.source === relation.target && r.target === relation.source && r.type === relation.type);
            seen.add(pairKey);

            const points = route(rectOf(source), rectOf(target), source, target);
            const path = document.createElementNS(NS, "path");
            path.setAttribute("d", points.map((p, i) => `${i ? "L" : "M"} ${p[0]} ${p[1]}`).join(" "));
            path.setAttribute("class", `relation-${relation.type}`);
            if (reverse) path.classList.add("is-both");
            path.dataset.dynamicLine = "1";
            path.dataset.source = relation.source;
            path.dataset.target = relation.target;
            const title = document.createElementNS(NS, "title");
            const a = processData[relation.source]?.name || "";
            const b = processData[relation.target]?.name || "";
            title.textContent = reverse ? `${a} ↔ ${b}` : `${a} → ${b}${relation.label ? `: ${relation.label}` : ""}`;
            path.appendChild(title);
            linksLayer.appendChild(path);

            if (reverse) {
                // La relación inversa también cuenta para el resaltado al pasar el mouse.
                const twin = path.cloneNode(false);
                twin.dataset.source = relation.target;
                twin.dataset.target = relation.source;
                twin.setAttribute("class", `relation-${relation.type} map-v2-twin`);
                linksLayer.appendChild(twin);
            }
        });
        if (typeof addHitAreas === "function") addHitAreas();
    }

    // ---------- Crear y retirar relaciones desde el mapa ----------
    const canChange = stage.dataset.canChange === "1";
    const relationUrl = stage.dataset.relationUrl;
    const draft = svg.querySelector("[data-map-draft]");
    const popover = stage.querySelector("[data-link-popover]");
    let linking = null;
    let selectedLink = null;

    function addHitAreas() {
        if (!canChange) return;
        linksLayer.querySelectorAll("path[data-dynamic-line]:not(.map-v2-twin)").forEach((path) => {
            const hit = document.createElementNS(NS, "path");
            hit.setAttribute("d", path.getAttribute("d"));
            hit.setAttribute("class", "map-v2-hit");
            hit.dataset.source = path.dataset.source;
            hit.dataset.target = path.dataset.target;
            hit.addEventListener("click", (event) => openPopover(event, hit));
            linksLayer.appendChild(hit);
        });
    }

    function nameOf(id) { return processData[id]?.name || "Proceso"; }

    function syncDetailLists(relation, added) {
        const a = processData[relation.source];
        const b = processData[relation.target];
        if (!a || !b) return;
        if (added) {
            a.outgoing.push({ id: relation.id, process: b.name });
            b.incoming.push({ id: relation.id, process: a.name });
        } else {
            a.outgoing = a.outgoing.filter((r) => r.id !== relation.id);
            b.incoming = b.incoming.filter((r) => r.id !== relation.id);
        }
        const current = nodes.find((n) => n.classList.contains("selected"));
        if (current && [relation.source, relation.target].includes(current.dataset.processId)) {
            renderDetail(current.dataset.processId);
        }
    }

    async function postForm(url, fields) {
        const body = new FormData();
        Object.entries(fields).forEach(([k, v]) => body.append(k, v));
        const response = await fetch(url, {
            method: "POST",
            headers: { "X-CSRFToken": cookie("csrftoken"), Accept: "application/json" },
            body,
        });
        const result = await response.json().catch(() => ({ ok: false }));
        if (!response.ok || !result.ok) throw new Error(result.error || "No se pudo completar la acción.");
        return result;
    }

    async function createRelation(sourceId, targetId) {
        if (sourceId === targetId) return;
        const exists = relations.some((r) => r.source === sourceId && r.target === targetId && r.type === "flow");
        if (exists) { setState(`Ya existe la relación ${nameOf(sourceId)} → ${nameOf(targetId)}`, "error"); return; }
        try {
            const { relation } = await postForm(relationUrl, { source: sourceId, target: targetId, relation_type: "flow", label: "" });
            relations.push(relation);
            drawLinks();
            syncDetailLists(relation, true);
            setState(`Relación creada: ${nameOf(sourceId)} → ${nameOf(targetId)}`, "saved");
        } catch (error) {
            setState(error.message, "error");
        }
    }

    function openPopover(event, hit) {
        event.stopPropagation();
        const relation = relations.find((r) => r.source === hit.dataset.source && r.target === hit.dataset.target);
        if (!relation) return;
        const reverse = relations.find((r) => r.source === relation.target && r.target === relation.source && r.type === relation.type);
        selectedLink = reverse ? [relation, reverse] : [relation];
        const p = stagePoint(event);
        popover.querySelector("[data-link-popover-title]").textContent = reverse
            ? `${nameOf(relation.source)} ↔ ${nameOf(relation.target)}`
            : `${nameOf(relation.source)} → ${nameOf(relation.target)}`;
        popover.querySelector("[data-link-remove]").textContent = reverse ? "Retirar ambas" : "Retirar relación";
        Object.assign(popover.style, { left: `${p.x + 10}px`, top: `${p.y + 10}px` });
        popover.hidden = false;
    }
    popover?.querySelector("[data-link-cancel]")?.addEventListener("click", () => { popover.hidden = true; });
    popover?.querySelector("[data-link-remove]")?.addEventListener("click", async () => {
        if (!selectedLink) return;
        try {
            for (const relation of selectedLink) {
                await postForm(relation.archive_url, {});
                relations.splice(relations.indexOf(relation), 1);
                syncDetailLists(relation, false);
            }
            drawLinks();
            setState("Relación retirada del mapa", "saved");
        } catch (error) {
            setState(error.message, "error");
        }
        popover.hidden = true;
    });
    document.addEventListener("click", (event) => {
        if (popover && !popover.hidden && !popover.contains(event.target)) popover.hidden = true;
    });

    nodes.forEach((node) => {
        const port = node.querySelector(".connect-port");
        if (!port) return;
        port.addEventListener("pointerdown", (event) => {
            event.preventDefault();
            event.stopPropagation();
            const r = rectOf(node);
            const start = node.dataset.kind === "output" ? [r.x, stagePoint(event).y] : [r.x + r.w, node.dataset.kind === "input" ? stagePoint(event).y : r.cy];
            linking = { node, start };
            stage.classList.add("is-linking");
            port.setPointerCapture(event.pointerId);
        });
        port.addEventListener("pointermove", (event) => {
            if (!linking) return;
            const p = stagePoint(event);
            draft.setAttribute("d", `M ${linking.start[0]} ${linking.start[1]} L ${p.x} ${p.y}`);
            nodes.forEach((n) => n.classList.remove("is-link-target"));
            const over = document.elementFromPoint(event.clientX, event.clientY)?.closest(".process-node");
            if (over && over !== node) over.classList.add("is-link-target");
        });
        const end = (event) => {
            if (!linking) return;
            const over = document.elementFromPoint(event.clientX, event.clientY)?.closest(".process-node");
            draft.setAttribute("d", "");
            stage.classList.remove("is-linking");
            nodes.forEach((n) => n.classList.remove("is-link-target"));
            const source = linking.node;
            linking = null;
            if (over && over !== source) createRelation(source.dataset.processId, over.dataset.processId);
        };
        port.addEventListener("pointerup", end);
        port.addEventListener("pointercancel", () => { linking = null; draft.setAttribute("d", ""); stage.classList.remove("is-linking"); });
        port.addEventListener("click", (event) => event.stopPropagation());
    });

    // Diálogo "Nueva relación" (botón de la cabecera y botón del panel).
    const relationDialog = document.querySelector("[data-relation-dialog]");
    function openRelationDialog(sourceId) {
        if (!relationDialog) return;
        const select = relationDialog.querySelector("select[name='source']");
        if (select && sourceId) select.value = sourceId;
        relationDialog.showModal();
    }
    document.querySelectorAll("[data-open-relation-dialog]").forEach((b) => b.addEventListener("click", () => openRelationDialog()));
    document.querySelectorAll("[data-close-relation-dialog]").forEach((b) => b.addEventListener("click", () => relationDialog?.close()));
    detail?.addEventListener("click", (event) => {
        const button = event.target.closest("[data-relation-from]");
        if (button) openRelationDialog(button.dataset.relationFrom);
    });

    // ---------- Zoom ----------
    function applyScale() {
        if (!geometry) return;
        stage.style.transform = `scale(${scale})`;
        sizer.style.width = `${geometry.width * scale}px`;
        sizer.style.height = `${geometry.height * scale}px`;
        const label = document.querySelector("[data-zoom-label]");
        if (label) label.textContent = `${Math.round(scale * 100)}%`;
    }
    function fit() {
        if (!geometry || !canvas) return;
        scale = Math.max(0.35, Math.min(1, (canvas.clientWidth - 24) / geometry.width));
        applyScale();
    }
    document.querySelector("[data-fit-map]")?.addEventListener("click", fit);
    document.querySelector("[data-zoom-in]")?.addEventListener("click", () => { scale = Math.min(1.6, scale + 0.1); applyScale(); });
    document.querySelector("[data-zoom-out]")?.addEventListener("click", () => { scale = Math.max(0.35, scale - 0.1); applyScale(); });
    document.querySelector("[data-fullscreen]")?.addEventListener("click", async () => {
        if (canvas?.requestFullscreen) { await canvas.requestFullscreen(); fit(); }
    });
    document.addEventListener("fullscreenchange", fit);

    // ---------- Arrastrar: mover y cambiar de categoría ----------
    function stagePoint(event) {
        const r = stage.getBoundingClientRect();
        return { x: (event.clientX - r.left) / scale, y: (event.clientY - r.top) / scale };
    }
    function laneAt(y) {
        const lanes = geometry.lanes;
        return lanes.find((l) => y >= l.top && y < l.top + l.height) || (y < lanes[0].top ? lanes[0] : lanes[lanes.length - 1]);
    }
    function setState(text, tone) {
        if (!saveState) return;
        saveState.textContent = text;
        saveState.dataset.tone = tone || "";
    }

    nodes.forEach((node) => {
        const handle = node.querySelector(".drag-handle");
        if (!handle) return;
        handle.addEventListener("pointerdown", (event) => {
            event.preventDefault();
            event.stopPropagation();
            const p = stagePoint(event);
            dragging = {
                node,
                dx: p.x - parseFloat(node.style.left),
                dy: p.y - parseFloat(node.style.top),
                moved: false,
            };
            node.classList.add("dragging");
            handle.setPointerCapture(event.pointerId);
        });
        handle.addEventListener("pointermove", (event) => {
            if (!dragging || dragging.node !== node) return;
            const p = stagePoint(event);
            const top = p.y - dragging.dy;
            const lane = laneAt(p.y);
            const x = Math.round(Math.max(0, Math.min(INNER_W - NODE_W, p.x - dragging.dx - geometry.boxLeft)));
            const y = Math.round(Math.max(30, Math.min(640, top - lane.top)));
            node.dataset.x = x;
            node.dataset.y = y;
            node.dataset.kind = lane.kind;
            node.dataset.category = lane.kind;
            dragging.moved = true;
            layout();
            lanesLayer.querySelector(`[data-lane="${lane.kind}"]`)?.classList.add("is-drop-target");
        });
        const finish = () => {
            if (!dragging || dragging.node !== node) return;
            node.classList.remove("dragging");
            if (dragging.moved) {
                const id = node.dataset.processId;
                pendingMoves.set(id, { id, x: Number(node.dataset.x), y: Number(node.dataset.y), category: node.dataset.kind });
                const name = processData[id]?.name || "El proceso";
                if (node.dataset.kind !== originalKind.get(id)) {
                    setState(`${name} pasará a ${LANE_NAMES[node.dataset.kind]}. Guarde para confirmar.`, "pending");
                } else {
                    setState(pendingMoves.size === 1 ? "1 cambio sin guardar" : `${pendingMoves.size} cambios sin guardar`, "pending");
                }
                node.dataset.justDragged = "1";
                setTimeout(() => delete node.dataset.justDragged, 0);
            }
            dragging = null;
            layout();
        };
        handle.addEventListener("pointerup", finish);
        handle.addEventListener("pointercancel", finish);
    });

    saveButton?.addEventListener("click", async () => {
        const moves = Array.from(pendingMoves.values());
        if (!moves.length) { setState("No hay cambios por guardar"); return; }
        saveButton.disabled = true;
        const label = saveButton.textContent;
        saveButton.textContent = "Guardando…";
        try {
            const response = await fetch("/procesos/mapa/guardar/", {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-CSRFToken": cookie("csrftoken") },
                body: JSON.stringify({ moves }),
            });
            const result = await response.json();
            if (!response.ok || !result.ok) throw new Error(result.error || "No se pudo guardar.");
            moves.forEach((m) => originalKind.set(m.id, m.category));
            pendingMoves.clear();
            setState(result.updated === 1 ? "Cambio guardado" : `${result.updated} cambios guardados`, "saved");
        } catch (error) {
            setState(error.message, "error");
        } finally {
            saveButton.disabled = false;
            saveButton.textContent = label;
        }
    });
    function cookie(name) {
        const item = document.cookie.split(";").map((c) => c.trim()).find((c) => c.startsWith(`${name}=`));
        return item ? decodeURIComponent(item.split("=")[1]) : "";
    }
    window.addEventListener("beforeunload", (event) => {
        if (pendingMoves.size) { event.preventDefault(); event.returnValue = ""; }
    });

    // ---------- Panel de detalle ----------
    const esc = (value) => {
        const div = document.createElement("div");
        div.textContent = String(value ?? "");
        return div.innerHTML;
    };

    function renderDetail(id) {
        const data = processData[id];
        if (!data || !detail) return;
        nodes.forEach((n) => n.classList.toggle("selected", n.dataset.processId === id));
        const party = data.kind === "input" || data.kind === "output";
        const kindText = party
            ? (data.kind === "input" ? "Parte interesada que entrega información" : "Parte interesada que recibe resultados")
            : `${data.category_name}${data.is_in_scope ? ", dentro del alcance" : ", fuera del alcance"}${data.is_external ? ", proceso externo" : ""}`;
        const flows = [
            ...data.incoming.map((r) => `<div>Recibe de <b>${esc(r.process)}</b></div>`),
            ...data.outgoing.map((r) => `<div>Entrega a <b>${esc(r.process)}</b></div>`),
        ].join("") || "<div>Sin relaciones registradas.</div>";
        const docs = data.documents.length
            ? data.documents.map((d) => `<a href="${d.url}"><b>${esc(d.code)}</b> ${esc(d.title)}</a>`).join("")
            : "<div>Sin documentos vinculados.</div>";

        detail.innerHTML = `
            <div class="process-detail-content">
                <header>
                    <h2>${esc(data.name)}</h2>
                    <span>${esc(kindText)}</span>
                </header>
                <div class="process-detail-actions">
                    <a class="outline-btn" href="${data.edit_url}">Editar</a>
                    <a class="outline-btn" href="${data.detail_url}">Abrir ficha</a>
                </div>
                <section class="process-detail-section">
                    <h3>Relaciones en el mapa</h3>
                    <div class="detail-links">${flows}</div>
                    ${canChange ? `<button type="button" class="outline-btn map-v2-add-link" data-relation-from="${id}">Nueva relación desde aquí</button>` : ""}
                </section>
                ${party ? "" : `
                <section class="process-detail-section">
                    <h3>Responsabilidad</h3>
                    <dl>
                        <div><dt>Puesto</dt><dd>${esc(data.owner_position || "Pendiente")}</dd></div>
                        <div><dt>Área</dt><dd>${esc(data.responsible_area || "Pendiente")}</dd></div>
                        <div><dt>Responsable actual</dt><dd>${data.owner_user ? `<a href="${data.owner_user.url}">${esc(data.owner_user.name)}</a>` : "Pendiente"}</dd></div>
                    </dl>
                </section>
                <section class="process-detail-section">
                    <h3>Descripción</h3>
                    <p>${esc(data.description || "Sin descripción.")}</p>
                </section>
                <section class="process-detail-section">
                    <h3>Involucrados</h3>
                    <p><b>Áreas:</b> ${esc(data.areas.join(", ") || "Sin áreas adicionales")}</p>
                    <p><b>Usuarios:</b> ${esc(data.participants.join(", ") || "Sin participantes directos")}</p>
                </section>
                <section class="process-detail-section">
                    <h3>Documentos vinculados</h3>
                    <div class="detail-links">${docs}</div>
                </section>`}
            </div>`;
    }

    nodes.forEach((node) => {
        node.addEventListener("click", (event) => {
            if (node.dataset.justDragged) { event.stopImmediatePropagation(); return; }
            renderDetail(node.dataset.processId);
        });
    });

    // ---------- Inicio ----------
    layout();
    fit();
    if (canvas && "ResizeObserver" in window) new ResizeObserver(() => fit()).observe(canvas);
    const first = nodes.find((n) => !isParty(n)) || nodes[0];
    if (first) renderDetail(first.dataset.processId);
    window.requestAnimationFrame(() => loader?.classList.add("is-ready"));
});
