const addChild = document.querySelector("#member-add-child");
const childTemplate = document.querySelector("#member-child-template");
const childList = document.querySelector("#member-children");
const childTotal = document.querySelector("#id_children-TOTAL_FORMS");
const childMaximum = document.querySelector("#id_children-MAX_NUM_FORMS");

function updateAddButton() {
    addChild.disabled = Number(childTotal.value) >= Number(childMaximum.value);
}

addChild.addEventListener("click", () => {
    const index = Number(childTotal.value);
    childList.insertAdjacentHTML("beforeend", childTemplate.innerHTML.replaceAll("__prefix__", String(index)));
    childTotal.value = index + 1;
    updateAddButton();
    childList.lastElementChild.querySelector('input[type="text"]')?.focus();
});

updateAddButton();

const manilaDate = new Intl.DateTimeFormat("sv-SE", {
    timeZone: "Asia/Manila",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
});

document.querySelectorAll("[data-member-age]").forEach((output) => {
    const birthDate = document.getElementById(output.getAttribute("for"));
    if (!birthDate) return;

    function updateAge() {
        const today = manilaDate.format(new Date());
        const birthday = birthDate.value;
        if (!birthday || birthday > today) {
            output.value = "—";
            return;
        }

        const [year, month, day] = today.split("-").map(Number);
        const [birthYear, birthMonth, birthDay] = birthday.split("-").map(Number);
        const birthdayPending = month < birthMonth || (month === birthMonth && day < birthDay);
        output.value = String(year - birthYear - Number(birthdayPending));
    }

    birthDate.addEventListener("input", updateAge);
    updateAge();
});
