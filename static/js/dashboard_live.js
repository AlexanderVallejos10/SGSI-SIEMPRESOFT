(() => {
    const body = document.body;
    const state = {
        metrics: [],
        objectives: [],
        controls: [],
        documents: [],
        evidence: [],
    };

    const api = {
        summary: body.dataset.apiSummary,
        metrics: body.dataset.apiMetrics,
        objectives: body.dataset.apiObjectives,
        controls: body.dataset.apiControls,
        documents: body.dataset.apiDocuments,
        evidence: body.dataset.apiEvidence,
    };

    const titles = {
        overview: ["Dashboard SGSI", "Vista ejecutiva conectada al ORM y al Dashboard SGSI 2026."],
        metrics: ["Rendimiento SGSI", "Indicadores y mediciones importados desde el Dashboard SGSI 2026."],
        objectives: ["Objetivos OESI", "Seguimiento de objetivos de seguridad de la información."],
        controls: ["Controles ISO 27001", "93 controles con trazabilidad documental y evidencia."],
        documents: ["Documentos SGSI", "Documentos controlados, versiones, secciones y controles relacionados."],
        evidence: ["Evidencias", "Repositorio trazable de evidencia y relaciones con controles."],
        traceability: ["Trazabilidad relacional", "Cómo se conectan las fuentes reales con el SGSI."],
    };

    const esc = (value) => String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");

    function yes(value) {
        return ["si", "sí", "yes", "true", "cumple"].includes(
            String(value || "").trim().toLowerCase()
        );
    }

    function badge(value, neutral = false) {
        const text = String(value || "Pendiente");
        let cls = "info";
        if (!neutral) {
            const n = text.toLowerCase();
            if (["si", "sí", "vigente", "active", "activo", "validado"].some(x => n.includes(x))) cls = "ok";
            else if (["no", "obsolete", "obsoleto", "inactivo"].some(x => n.includes(x))) cls = "bad";
            else if (["pendiente", "draft", "borrador", "sin"].some(x => n.includes(x))) cls = "warn";
        }
        return `<span class="badge ${cls}">${esc(text)}</span>`;
    }

    async function fetchJSON(url) {
        const response = await fetch(url, {
            credentials: "same-origin",
            headers: { "X-Requested-With": "XMLHttpRequest" },
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
    }

    function showSection(name) {
        document.querySelectorAll(".live-section").forEach(el => {
            el.classList.toggle("active", el.id === `section-${name}`);
        });
        document.querySelectorAll(".live-nav[data-section]").forEach(el => {
            el.classList.toggle("active", el.dataset.section === name);
        });
        const [title, subtitle] = titles[name] || titles.overview;
        document.getElementById("pageTitle").textContent = title;
        document.getElementById("pageSubtitle").textContent = subtitle;
        window.scrollTo({ top: 0, behavior: "smooth" });
    }

    function bindNavigation() {
        document.querySelectorAll("[data-section]").forEach(el => {
            el.addEventListener("click", () => showSection(el.dataset.section));
        });
        document.querySelectorAll("[data-go]").forEach(el => {
            el.addEventListener("click", () => showSection(el.dataset.go));
        });
    }

    function renderMetrics(items = state.metrics) {
        const tbody = document.getElementById("metricsTable");
        if (!items.length) {
            tbody.innerHTML = `<tr><td class="empty-row" colspan="7">Sin métricas.</td></tr>`;
            return;
        }
        tbody.innerHTML = items.map(item => `
            <tr>
                <td><b>${esc(item.measurement_id)}</b></td>
                <td>${esc(item.description)}</td>
                <td>${badge(item.pdca_cycle, true)}</td>
                <td>${esc(item.responsible)}</td>
                <td>${esc(item.indicator)}</td>
                <td><b>${esc(item.current_value)}</b></td>
                <td>${badge(item.compliance)}</td>
            </tr>
        `).join("");
    }

    function renderObjectives(items = state.objectives) {
        const tbody = document.getElementById("objectivesTable");
        if (!items.length) {
            tbody.innerHTML = `<tr><td class="empty-row" colspan="8">Sin objetivos.</td></tr>`;
            return;
        }
        tbody.innerHTML = items.map(item => `
            <tr>
                <td><b>${esc(item.measurement_id)}</b></td>
                <td>${esc(item.description)}</td>
                <td>${esc(item.responsible)}</td>
                <td>${esc(item.period)}</td>
                <td>${esc(item.indicator)}</td>
                <td><b>${esc(item.current_value)}</b></td>
                <td>${badge(item.compliance)}</td>
                <td>${badge(item.source_override || "—", true)}</td>
            </tr>
        `).join("");
    }

    function renderControls(items = state.controls) {
        const tbody = document.getElementById("controlsTable");
        if (!items.length) {
            tbody.innerHTML = `<tr><td class="empty-row" colspan="6">Sin controles para el filtro actual.</td></tr>`;
            return;
        }
        tbody.innerHTML = items.map(item => `
            <tr data-control-id="${esc(item.id)}">
                <td><b>${esc(item.code)}</b></td>
                <td>${esc(item.name)}</td>
                <td>${esc(item.domain)}</td>
                <td>${badge(item.document_count, true)}</td>
                <td>${badge(item.evidence_count, true)}</td>
                <td>${item.validated_evidence_count ? badge(item.validated_evidence_count, true) : badge("0", true)}</td>
            </tr>
        `).join("");

        tbody.querySelectorAll("[data-control-id]").forEach(row => {
            row.addEventListener("click", () => openControl(row.dataset.controlId));
        });
    }

    function renderDocuments(items = state.documents) {
        const tbody = document.getElementById("documentsTable");
        if (!items.length) {
            tbody.innerHTML = `<tr><td class="empty-row" colspan="7">Sin documentos.</td></tr>`;
            return;
        }
        tbody.innerHTML = items.map(item => `
            <tr data-document-id="${esc(item.id)}">
                <td><b>${esc(item.code)}</b></td>
                <td>${esc(item.title)}</td>
                <td>${esc(item.document_type || "—")}</td>
                <td>${badge(item.status || "pendiente")}</td>
                <td>${esc(item.version_count)}</td>
                <td>${esc(item.section_count)}</td>
                <td>${esc(item.control_count)}</td>
            </tr>
        `).join("");

        tbody.querySelectorAll("[data-document-id]").forEach(row => {
            row.addEventListener("click", () => openDocument(row.dataset.documentId));
        });
    }

    function renderEvidence(items = state.evidence) {
        const tbody = document.getElementById("evidenceTable");
        if (!items.length) {
            tbody.innerHTML = `<tr><td class="empty-row" colspan="5">Sin evidencias.</td></tr>`;
            return;
        }
        tbody.innerHTML = items.map(item => `
            <tr>
                <td><b>${esc(item.code)}</b></td>
                <td>${esc(item.description)}</td>
                <td>${esc(item.source_file || "—")}</td>
                <td>${badge(item.classification, true)}</td>
                <td>${item.control_count ? badge(item.control_count, true) : badge("0", true)}</td>
            </tr>
        `).join("");
    }

    function filterList(list, query, fields) {
        const q = String(query || "").trim().toLowerCase();
        if (!q) return list;
        return list.filter(item => fields.some(field =>
            String(item[field] || "").toLowerCase().includes(q)
        ));
    }

    function bindFilters() {
        document.getElementById("metricsSearch").addEventListener("input", e => {
            renderMetrics(filterList(state.metrics, e.target.value, ["measurement_id", "description", "responsible", "process"]));
        });

        document.getElementById("objectivesSearch").addEventListener("input", e => {
            renderObjectives(filterList(state.objectives, e.target.value, ["measurement_id", "description", "responsible"]));
        });

        const filterControls = () => {
            let items = filterList(state.controls, document.getElementById("controlsSearch").value, ["code", "name", "domain"]);
            if (document.getElementById("controlsWithoutDocs").checked) {
                items = items.filter(item => Number(item.document_count) === 0);
            }
            renderControls(items);
        };
        document.getElementById("controlsSearch").addEventListener("input", filterControls);
        document.getElementById("controlsWithoutDocs").addEventListener("change", filterControls);

        document.getElementById("documentsSearch").addEventListener("input", e => {
            renderDocuments(filterList(state.documents, e.target.value, ["code", "title", "document_type", "category"]));
        });

        document.getElementById("evidenceSearch").addEventListener("input", e => {
            renderEvidence(filterList(state.evidence, e.target.value, ["code", "description", "source_file"]));
        });
    }

    const modal = document.getElementById("detailModal");
    const modalBody = document.getElementById("modalBody");

    function openModal(html) {
        modalBody.innerHTML = html;
        modal.classList.add("open");
        modal.setAttribute("aria-hidden", "false");
    }

    function closeModal() {
        modal.classList.remove("open");
        modal.setAttribute("aria-hidden", "true");
    }

    document.querySelectorAll("[data-close-modal]").forEach(el => {
        el.addEventListener("click", closeModal);
    });

    async function openControl(id) {
        openModal(`<div class="loading">Cargando control y relaciones...</div>`);
        try {
            const base = api.controls.replace(/controls\/?$/, "");
            const data = await fetchJSON(`${base}control/${id}/`);
            openModal(`
                <p class="eyebrow">CONTROL ISO 27001:2022</p>
                <h2>${esc(data.code)} · ${esc(data.name)}</h2>
                <div class="detail-meta">
                    ${badge(data.domain, true)}
                    ${badge(data.applicability, true)}
                    ${badge(data.implementation_status, true)}
                    ${badge(`${data.compliance_percent}%`, true)}
                </div>
                <h4>Documentos relacionados (${data.documents.length})</h4>
                ${data.documents.length ? data.documents.map(row => `
                    <div class="detail-item">
                        <strong>${esc(row.code)} · ${esc(row.title)}</strong>
                        <p>${esc(row.method)} · confianza ${esc(row.confidence)}%</p>
                    </div>
                `).join("") : `<div class="detail-item"><p>Sin documento automático relacionado.</p></div>`}
                <h4>Evidencias relacionadas (${data.evidence.length})</h4>
                ${data.evidence.length ? data.evidence.map(row => `
                    <div class="detail-item">
                        <strong>${esc(row.code)} · ${esc(row.description)}</strong>
                        <p>${row.validated ? "Validada" : "Pendiente de validación funcional"}</p>
                    </div>
                `).join("") : `<div class="detail-item"><p>Sin evidencia relacionada.</p></div>`}
            `);
        } catch (error) {
            openModal(`<h2>Error</h2><p>No fue posible cargar el control.</p>`);
        }
    }

    async function openDocument(id) {
        openModal(`<div class="loading">Cargando documento y relaciones...</div>`);
        try {
            const base = api.documents.replace(/documents\/?$/, "");
            const data = await fetchJSON(`${base}document/${id}/`);
            openModal(`
                <p class="eyebrow">DOCUMENTO SGSI</p>
                <h2>${esc(data.code)} · ${esc(data.title)}</h2>
                <div class="detail-meta">
                    ${badge(data.document_type || "sin tipo", true)}
                    ${badge(data.status)}
                    ${badge(data.classification, true)}
                </div>
                <h4>Secciones del Manual SGSI (${data.sections.length})</h4>
                ${data.sections.length ? data.sections.map(row => `
                    <div class="detail-item">
                        <strong>${esc(row.code)} · ${esc(row.title)}</strong>
                    </div>
                `).join("") : `<div class="detail-item"><p>Sin sección asignada.</p></div>`}
                <h4>Controles relacionados (${data.controls.length})</h4>
                ${data.controls.length ? data.controls.map(row => `
                    <div class="detail-item">
                        <strong>${esc(row.code)} · ${esc(row.name)}</strong>
                        <p>${esc(row.method)} · confianza ${esc(row.confidence)}%</p>
                    </div>
                `).join("") : `<div class="detail-item"><p>Sin control relacionado.</p></div>`}
                <h4>Versiones (${data.versions.length})</h4>
                ${data.versions.map(row => `
                    <div class="detail-item">
                        <strong>Versión ${esc(row.version)} · ${esc(row.status)}</strong>
                        <p>${esc(row.source_file || row.source_artifact || "Sin fuente")}</p>
                    </div>
                `).join("")}
            `);
        } catch (error) {
            openModal(`<h2>Error</h2><p>No fue posible cargar el documento.</p>`);
        }
    }

    async function loadData() {
        try {
            const [summary, metrics, objectives, controls, documents, evidence] = await Promise.all([
                fetchJSON(api.summary),
                fetchJSON(api.metrics),
                fetchJSON(api.objectives),
                fetchJSON(api.controls),
                fetchJSON(api.documents),
                fetchJSON(api.evidence),
            ]);

            state.metrics = metrics.items || [];
            state.objectives = objectives.items || [];
            state.controls = controls.items || [];
            state.documents = documents.items || [];
            state.evidence = evidence.items || [];

            document.getElementById("menuMetrics").textContent = summary.counts.metrics;
            document.getElementById("menuObjectives").textContent = summary.counts.objectives;
            document.getElementById("menuControls").textContent = summary.counts.controls;
            document.getElementById("menuDocuments").textContent = summary.counts.documents;
            document.getElementById("menuEvidence").textContent = summary.counts.evidence;
            document.getElementById("snapshotCode").textContent = summary.snapshot.code;

            renderMetrics();
            renderObjectives();
            renderControls();
            renderDocuments();
            renderEvidence();
        } catch (error) {
            console.error("No se pudo cargar Dashboard SGSI:", error);
        }
    }

    bindNavigation();
    bindFilters();
    loadData();
})();
