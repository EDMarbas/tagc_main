const editMemberForm = document.querySelector("[data-highlight-blank]");

function highlightBlankFields() {
    const controls = Array.from(editMemberForm.elements).filter(
        (control) => control.matches("input[name], select[name], textarea[name]") && !control.disabled,
    );

    for (const control of controls) {
        let blank;
        switch (control.type) {
            case "hidden":
            case "range":
            case "submit":
            case "button":
                continue;
            case "checkbox":
            case "radio": {
                const group = controls.filter((candidate) => candidate.name === control.name);
                blank = (control.type === "radio" || group.length > 1)
                    && !group.some((option) => option.checked);
                break;
            }
            case "file":
                blank = !control.files.length && !editMemberForm.hasAttribute("data-has-photo");
                break;
            case "select-one":
                blank = !control.value || control.value === "unknown";
                break;
            default:
                blank = !control.value.trim();
        }
        control.classList.toggle("member-field-blank", blank);
    }
}

if (editMemberForm) {
    editMemberForm.addEventListener("input", highlightBlankFields);
    editMemberForm.addEventListener("change", highlightBlankFields);
    new MutationObserver(highlightBlankFields).observe(
        editMemberForm.querySelector("#member-children"), {childList: true},
    );
    highlightBlankFields();
}
