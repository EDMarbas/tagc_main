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
