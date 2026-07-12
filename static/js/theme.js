(function () {
    "use strict";

    const STORAGE_KEY = "transitops-theme";
    const root = document.documentElement;

    function getSavedTheme() {
        try {
            return localStorage.getItem(STORAGE_KEY);
        } catch (error) {
            return null;
        }
    }

    function saveTheme(theme) {
        try {
            localStorage.setItem(STORAGE_KEY, theme);
        } catch (error) {
            console.warn("Could not save theme preference.");
        }
    }

    function getSystemTheme() {
        return window.matchMedia(
            "(prefers-color-scheme: dark)"
        ).matches
            ? "dark"
            : "light";
    }

    function getCurrentTheme() {
        return (
            root.getAttribute("data-bs-theme")
            || getSavedTheme()
            || getSystemTheme()
        );
    }

    function updateToggleButton(theme) {
        const button = document.getElementById(
            "themeToggle"
        );

        const icon = document.getElementById(
            "themeToggleIcon"
        );

        const text = document.getElementById(
            "themeToggleText"
        );

        if (!button) {
            return;
        }

        const isDark = theme === "dark";

        button.setAttribute(
            "aria-pressed",
            isDark ? "true" : "false"
        );

        button.setAttribute(
            "title",
            isDark
                ? "Switch to light mode"
                : "Switch to dark mode"
        );

        if (icon) {
            icon.className = isDark
                ? "bi bi-sun-fill"
                : "bi bi-moon-stars-fill";
        }

        if (text) {
            text.textContent = isDark
                ? "Light"
                : "Dark";
        }
    }

    function updateCharts(theme) {
        if (
            typeof window.Chart === "undefined"
            || !window.Chart.instances
        ) {
            return;
        }

        const isDark = theme === "dark";

        const textColor = isDark
            ? "#cbd5e1"
            : "#475569";

        const gridColor = isDark
            ? "rgba(148, 163, 184, 0.16)"
            : "rgba(100, 116, 139, 0.14)";

        Object.values(
            window.Chart.instances
        ).forEach(function (chart) {
            if (!chart || !chart.options) {
                return;
            }

            if (chart.options.plugins) {
                if (chart.options.plugins.legend) {
                    chart.options.plugins.legend.labels =
                        chart.options.plugins.legend.labels
                        || {};

                    chart.options.plugins.legend.labels.color =
                        textColor;
                }

                if (chart.options.plugins.title) {
                    chart.options.plugins.title.color =
                        textColor;
                }
            }

            if (chart.options.scales) {
                Object.values(
                    chart.options.scales
                ).forEach(function (scale) {
                    scale.ticks = scale.ticks || {};
                    scale.grid = scale.grid || {};
                    scale.title = scale.title || {};

                    scale.ticks.color = textColor;
                    scale.grid.color = gridColor;
                    scale.title.color = textColor;
                });
            }

            chart.update("none");
        });
    }

    function applyTheme(
        theme,
        persist
    ) {
        const safeTheme = theme === "dark"
            ? "dark"
            : "light";

        root.setAttribute(
            "data-bs-theme",
            safeTheme
        );

        root.setAttribute(
            "data-theme",
            safeTheme
        );

        if (persist) {
            saveTheme(safeTheme);
        }

        updateToggleButton(safeTheme);

        window.requestAnimationFrame(
            function () {
                updateCharts(safeTheme);
            }
        );

        /*
         * This delayed update also catches dashboard charts
         * created after this script initially runs.
         */
        window.setTimeout(
            function () {
                updateCharts(safeTheme);
            },
            150
        );

        window.dispatchEvent(
            new CustomEvent(
                "transitops:themechange",
                {
                    detail: {
                        theme: safeTheme,
                    },
                }
            )
        );
    }

    document.addEventListener(
        "DOMContentLoaded",
        function () {
            const initialTheme = (
                getSavedTheme()
                || getSystemTheme()
            );

            applyTheme(
                initialTheme,
                false
            );

            const toggleButton =
                document.getElementById(
                    "themeToggle"
                );

            if (toggleButton) {
                toggleButton.addEventListener(
                    "click",
                    function () {
                        const nextTheme =
                            getCurrentTheme()
                            === "dark"
                                ? "light"
                                : "dark";

                        applyTheme(
                            nextTheme,
                            true
                        );
                    }
                );
            }

            const systemPreference =
                window.matchMedia(
                    "(prefers-color-scheme: dark)"
                );

            systemPreference.addEventListener(
                "change",
                function (event) {
                    /*
                     * Follow system changes only when the user
                     * has not manually selected a theme.
                     */
                    if (!getSavedTheme()) {
                        applyTheme(
                            event.matches
                                ? "dark"
                                : "light",
                            false
                        );
                    }
                }
            );
        }
    );

    window.TransitOpsTheme = {
        apply: function (theme) {
            applyTheme(
                theme,
                true
            );
        },

        current: getCurrentTheme,
        updateCharts: updateCharts,
    };
})();