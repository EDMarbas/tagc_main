{
    const input = document.querySelector(".application-photo input[type=file]");
    const editor = document.querySelector("#photo-editor");
    const canvas = document.querySelector("#photo-preview");
    const context = canvas.getContext("2d");
    const status = document.querySelector("#photo-preview-status");
    const zoom = document.querySelector("#photo-zoom");
    const horizontal = document.querySelector("#photo-horizontal");
    const vertical = document.querySelector("#photo-vertical");
    const controls = [zoom, horizontal, vertical];
    let image;
    let loading = false;
    let selection = 0;

    function drawPreview() {
        const size = canvas.width;
        const scale = Math.max(size / image.naturalWidth, size / image.naturalHeight) * zoom.valueAsNumber / 100;
        const width = image.naturalWidth * scale;
        const height = image.naturalHeight * scale;
        const x = (size - width) / 2 + Math.max(0, width - size) / 2 * horizontal.valueAsNumber / 100;
        const y = (size - height) / 2 + Math.max(0, height - size) / 2 * vertical.valueAsNumber / 100;

        context.fillStyle = "#fff";
        context.fillRect(0, 0, size, size);
        context.drawImage(image, x, y, width, height);
    }

    function resetCrop() {
        controls.forEach((control) => { control.value = control.defaultValue; });
        if (image) drawPreview();
    }

    if (context && "FormDataEvent" in window) {
        input.addEventListener("change", async () => {
            const currentSelection = ++selection;
            const file = input.files[0];
            image = undefined;
            loading = false;
            editor.hidden = true;
            status.textContent = "";
            if (!file || (file.type && !["image/jpeg", "image/png"].includes(file.type)) || file.size > 2 * 1024 * 1024) return;

            const url = URL.createObjectURL(file);
            const preview = new Image();
            loading = true;
            try {
                preview.src = url;
                await preview.decode();
                if (currentSelection !== selection || preview.naturalWidth * preview.naturalHeight > 20_000_000) return;
                image = preview;
                resetCrop();
                editor.hidden = false;
                status.textContent = "";
            } catch {
                if (currentSelection === selection) status.textContent = "Photo preview unavailable. Choose another photo to adjust the crop.";
            } finally {
                URL.revokeObjectURL(url);
                if (currentSelection === selection) loading = false;
            }
        });

        controls.forEach((control) => control.addEventListener("input", drawPreview));
        document.querySelector("#photo-reset").addEventListener("click", resetCrop);
        input.form.addEventListener("submit", (event) => {
            if (loading) {
                event.preventDefault();
                status.textContent = "Wait for the photo preview before saving.";
            }
        });
        input.form.addEventListener("formdata", (event) => {
            if (!image || !input.files.length) return;
            const encoded = canvas.toDataURL("image/jpeg", 0.92).split(",")[1];
            const bytes = Uint8Array.from(atob(encoded), (character) => character.charCodeAt(0));
            event.formData.set(input.name, new File([bytes], "member-photo.jpg", {type: "image/jpeg"}));
        });
    }
}
