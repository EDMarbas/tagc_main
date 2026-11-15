const requestDialog = document.querySelector("#membership-request");
const candidateInput = requestDialog.querySelector("[name=candidate]");
const fullNameInput = requestDialog.querySelector("[name=full_name]");

document.querySelectorAll("[data-membership-request]").forEach((button) => {
    button.addEventListener("click", () => {
        candidateInput.value = button.dataset.membershipRequest;
        fullNameInput.value = button.dataset.memberName || "";
        requestDialog.showModal();
    });
});

document.querySelector("#close-membership-request").addEventListener("click", () => requestDialog.close());
if (requestDialog.dataset.reopen === "yes") requestDialog.showModal();
