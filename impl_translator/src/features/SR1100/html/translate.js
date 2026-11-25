const form = document.getElementById("translate-form");
const direction = document.getElementById("direction");
const source = document.getElementById("source");
const translation = document.getElementById("translation");
const button = document.getElementById("submit");
const statusMessage = document.getElementById("status");

form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (button.disabled) return;

    translation.value = "";
    statusMessage.removeAttribute("data-error");
    statusMessage.textContent = "翻訳中…";
    button.disabled = true;
    source.readOnly = true;
    direction.disabled = true;

    try {
        const response = await fetch("/sr1100/api/translate", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({text: source.value, direction: direction.value}),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error ?? "翻訳に失敗しました。");
        translation.value = data.translation;
        statusMessage.textContent = "翻訳が完了しました。";
    } catch (error) {
        statusMessage.setAttribute("data-error", "");
        statusMessage.textContent = error.message;
    } finally {
        button.disabled = false;
        source.readOnly = false;
        direction.disabled = false;
    }
});
