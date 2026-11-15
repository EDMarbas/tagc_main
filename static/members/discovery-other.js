const otherDiscovery = document.querySelector('input[name="discovery_sources"][value="Other"]');
const discoveryDialog = document.querySelector("[data-discovery-dialog]");
const discoveryDetails = document.querySelector("[data-discovery-details]");

if (otherDiscovery && discoveryDetails && typeof discoveryDialog?.showModal === "function") {
    const answer = discoveryDetails.querySelector("textarea");
    const sources = Array.from(otherDiscovery.form.elements.discovery_sources);
    let previousSource = sources.find((source) => source !== otherDiscovery && source.checked);
    discoveryDialog.querySelector("[data-discovery-input]").append(discoveryDetails);

    function openDiscoveryDialog() {
        if (otherDiscovery.checked && !discoveryDialog.open) {
            discoveryDialog.showModal();
            answer.focus();
        }
    }

    for (const source of sources) {
        source.addEventListener("change", () => {
            if (source !== otherDiscovery && source.checked) previousSource = source;
            openDiscoveryDialog();
        });
    }
    otherDiscovery.addEventListener("click", openDiscoveryDialog);
    discoveryDialog.querySelector("[data-discovery-close]").addEventListener("click", () => discoveryDialog.close());
    answer.addEventListener("input", () => answer.setCustomValidity(""));
    discoveryDialog.querySelector("[data-discovery-done]").addEventListener("click", () => {
        if (!answer.value.trim()) {
            answer.setCustomValidity("Enter how you heard about TAGC.");
            answer.reportValidity();
            return;
        }
        discoveryDialog.close();
    });
    discoveryDialog.addEventListener("close", () => {
        answer.setCustomValidity("");
        if (!answer.value.trim()) {
            otherDiscovery.checked = false;
            if (previousSource) previousSource.checked = true;
            (previousSource || otherDiscovery).focus();
        }
    });

    if (otherDiscovery.checked && discoveryDetails.querySelector(".errorlist")) {
        openDiscoveryDialog();
    }
}
