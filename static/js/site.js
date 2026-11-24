const navigationToggle = document.querySelector(".navigation-toggle");
const navigationLinks = document.querySelector("#main-navigation-links");
const compactNavigation = window.matchMedia("(max-width: 64rem)");
const accountMenu = document.querySelector(".account-menu");

if (accountMenu) {
    const accountToggle = accountMenu.querySelector("summary");
    accountMenu.addEventListener("focusout", (event) => {
        if (event.relatedTarget && !accountMenu.contains(event.relatedTarget)) accountMenu.open = false;
    });
    document.addEventListener("click", (event) => {
        if (accountMenu.open && !accountMenu.contains(event.target)) accountMenu.open = false;
    });
    accountMenu.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && accountMenu.open) {
            event.stopPropagation();
            accountMenu.open = false;
            accountToggle.focus();
        }
    });
}

function setNavigation(open) {
    navigationLinks.hidden = compactNavigation.matches && !open;
    navigationToggle.hidden = !compactNavigation.matches;
    navigationToggle.setAttribute("aria-expanded", String(compactNavigation.matches && open));
}

if (navigationToggle && navigationLinks) {
    setNavigation(false);
    compactNavigation.addEventListener("change", () => {
        const focusWasInside = navigationLinks.contains(document.activeElement);
        const toggleWasFocused = document.activeElement === navigationToggle;
        setNavigation(false);
        if (compactNavigation.matches && focusWasInside) navigationToggle.focus();
        if (!compactNavigation.matches && toggleWasFocused) navigationLinks.querySelector("a")?.focus();
    });
    navigationToggle.addEventListener("click", () => {
        const open = navigationToggle.getAttribute("aria-expanded") !== "true";
        setNavigation(open);
        if (open && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
            navigationLinks.animate?.(
                [{opacity: 0, transform: "translateY(-4px)"}, {opacity: 1, transform: "translateY(0)"}],
                {duration: 160, easing: "ease-out"},
            );
        }
    });
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && navigationToggle.getAttribute("aria-expanded") === "true"
            && navigationToggle.closest("nav").contains(document.activeElement)) {
            setNavigation(false);
            navigationToggle.focus();
        }
    });
}

if (navigationToggle && navigationLinks) {
    navigationLinks.addEventListener("click", (event) => {
        if (compactNavigation.matches && event.target.closest("a")) setNavigation(false);
    });
}
