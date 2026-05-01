(() => {
    "use strict";

    const getStoredTheme = () => localStorage.getItem("theme") || "dark";

    const theme = getStoredTheme();
    document.documentElement.setAttribute("data-bs-theme", theme);

    const showActiveTheme = (theme) => {
        const themeSwitcher = document.querySelector('#bd-theme');
        const btnToActivate = document.querySelector(`[data-bs-theme-value="${theme}"]`);
        
        if (!themeSwitcher || !btnToActivate) return;

        const activeIcon = btnToActivate.querySelector('svg use');
        const mainIcon = themeSwitcher.querySelector('svg use');
        
        if (activeIcon && mainIcon) {
            mainIcon.setAttribute('href', activeIcon.getAttribute('href'));
        }

        document.querySelectorAll("[data-bs-theme-value]").forEach(el => {
            el.classList.remove("active");
            el.setAttribute("aria-pressed", "false");
        });

        btnToActivate.classList.add("active");
        btnToActivate.setAttribute("aria-pressed", "true");
    };

    window.addEventListener("DOMContentLoaded", () => {
        showActiveTheme(getStoredTheme());

        document.querySelectorAll("[data-bs-theme-value]").forEach((toggle) => {
            toggle.addEventListener("click", () => {
                const selectedTheme = toggle.getAttribute("data-bs-theme-value");
                localStorage.setItem("theme", selectedTheme);
                document.documentElement.setAttribute("data-bs-theme", selectedTheme);
                showActiveTheme(selectedTheme);
            });
        });
    });
})();
