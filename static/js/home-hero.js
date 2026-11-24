const heroTitle = document.querySelector("#home-title");
const heroTitleLines = Array.from(heroTitle.querySelectorAll("span"));
let heroTitleWidth;

function fitHeroTitle() {
    const available = heroTitle.clientWidth;
    const widestLine = Math.max(...heroTitleLines.map((line) => line.getBoundingClientRect().width));
    if (available <= 1 || widestLine <= 0) return;

    const currentSize = parseFloat(getComputedStyle(heroTitle).fontSize);
    heroTitle.style.setProperty("--hero-title-size", `${currentSize * (available - 1) / widestLine}px`);
}

new ResizeObserver(() => {
    if (heroTitleWidth === heroTitle.clientWidth) return;
    heroTitleWidth = heroTitle.clientWidth;
    fitHeroTitle();
}).observe(heroTitle);

document.fonts.ready.then(fitHeroTitle);

const progressNotice = document.querySelector("#home-progress");
const progressNoticeKey = "tagc-home-progress-seen";

function showProgressNotice() {
    if (!progressNotice || typeof progressNotice.showModal !== "function") return;

    try {
        if (sessionStorage.getItem(progressNoticeKey)) return;
    } catch {
        // The notice can still open when browser storage is unavailable.
    }

    progressNotice.showModal();
    try {
        sessionStorage.setItem(progressNoticeKey, "1");
    } catch {
        // Dismissal still works without browser storage.
    }
}

showProgressNotice();
