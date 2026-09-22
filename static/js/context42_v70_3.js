document.addEventListener(
    "DOMContentLoaded",
    () => {
        const cards = document.querySelectorAll(
            "[data-context42-card]"
        );

        cards.forEach(
            (card) => {
                card.addEventListener(
                    "toggle",
                    () => {
                        if (!card.open) {
                            return;
                        }

                        cards.forEach(
                            (other) => {
                                if (
                                    other
                                    !== card
                                ) {
                                    other.open = false;
                                }
                            }
                        );
                    }
                );
            }
        );

        const params = new URLSearchParams(
            window.location.search
        );

        const openSlug = params.get(
            "open"
        );

        if (openSlug) {
            const target = document.querySelector(
                `[data-document-slug="${CSS.escape(openSlug)}"]`
            );

            if (target) {
                cards.forEach(
                    (card) => {
                        card.open = (
                            card
                            === target
                        );
                    }
                );
            }
        }

        const partySearch = document.querySelector(
            "[data-party-search]"
        );

        if (partySearch) {
            partySearch.addEventListener(
                "input",
                () => {
                    const query = (
                        partySearch
                        .value
                        .trim()
                        .toLowerCase()
                    );

                    document.querySelectorAll(
                        "[data-party-block]"
                    ).forEach(
                        (block) => {
                            const haystack = (
                                block.dataset.partySearch
                                || ""
                            );

                            const show = (
                                !query
                                || haystack.includes(
                                    query
                                )
                            );

                            block.style.display = (
                                show
                                ? ""
                                : "none"
                            );
                        }
                    );
                }
            );
        }

        const legalSearch = document.querySelector(
            "[data-legal-search]"
        );

        const promulgator = document.querySelector(
            "[data-legal-promulgator]"
        );

        const responsible = document.querySelector(
            "[data-legal-responsible]"
        );

        const status = document.querySelector(
            "[data-legal-status]"
        );

        const count = document.querySelector(
            "[data-legal-count]"
        );

        function normalize(value) {
            return String(
                value
                || ""
            )
            .trim()
            .toLowerCase();
        }

        function filterLegal() {
            const query = normalize(
                legalSearch?.value
            );

            const prom = normalize(
                promulgator?.value
            );

            const resp = normalize(
                responsible?.value
            );

            const state = normalize(
                status?.value
            );

            let visible = 0;

            document.querySelectorAll(
                "[data-legal-row]"
            ).forEach(
                (row) => {
                    const matchesQuery = (
                        !query
                        || normalize(
                            row.dataset.search
                        ).includes(
                            query
                        )
                    );

                    const matchesProm = (
                        !prom
                        || normalize(
                            row.dataset.promulgator
                        ) === prom
                    );

                    const matchesResp = (
                        !resp
                        || normalize(
                            row.dataset.responsible
                        ) === resp
                    );

                    const matchesState = (
                        !state
                        || normalize(
                            row.dataset.status
                        ) === state
                    );

                    const show = (
                        matchesQuery
                        && matchesProm
                        && matchesResp
                        && matchesState
                    );

                    row.style.display = (
                        show
                        ? ""
                        : "none"
                    );

                    if (show) {
                        visible += 1;
                    }
                }
            );

            if (count) {
                count.textContent = (
                    `${visible} registro`
                    + (
                        visible === 1
                        ? ""
                        : "s"
                    )
                );
            }
        }

        [
            legalSearch,
            promulgator,
            responsible,
            status,
        ]
        .filter(Boolean)
        .forEach(
            (control) => {
                control.addEventListener(
                    (
                        control.tagName
                        === "INPUT"
                    )
                    ? "input"
                    : "change",
                    filterLegal,
                );
            }
        );
    }
);
