const form = document.getElementById("question-form");
const question = document.getElementById("question");
const keepHistory = document.getElementById("keep-history");
const clearHistory = document.getElementById("clear-history");
const submit = document.getElementById("submit");
const statusMessage = document.getElementById("status");
const messages = document.getElementById("messages");
let historyMessages = [];

function setStatus(text, error = false) {
    statusMessage.textContent = text;
    statusMessage.toggleAttribute("data-error", error);
}

function resetHistory() {
    historyMessages = [];
    clearHistory.disabled = true;
    messages.replaceChildren();
    setStatus("");
}

keepHistory.addEventListener("change", () => {
    if (!keepHistory.checked) resetHistory();
});
clearHistory.addEventListener("click", resetHistory);

form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (submit.disabled) return;

    const text = question.value;
    const carry = keepHistory.checked;
    setStatus("回答を生成中…");
    submit.disabled = true;
    keepHistory.disabled = true;
    clearHistory.disabled = true;
    question.readOnly = true;

    try {
        const response = await fetch("/sr1200/api/ask", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({text, keep_history: carry, history: historyMessages}),
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error ?? "回答の生成に失敗しました。");

        historyMessages = result.history;
        let displayed = historyMessages;
        if (!carry) {
            displayed = [{role: "user", content: text}, {role: "assistant", content: result.answer}];
        }
        messages.replaceChildren(...displayed.map(({role, content}) => {
            const item = document.createElement("article");
            item.dataset.role = role;
            const heading = document.createElement("h2");
            heading.textContent = role === "user" ? "質問" : "回答";
            const body = document.createElement("p");
            body.textContent = content;
            item.append(heading, body);
            return item;
        }));
        question.value = "";
        const details = [];
        if (carry && Number.isInteger(result.prompt_tokens)) {
            details.push(`入力 ${result.prompt_tokens.toLocaleString()} / ${result.context_tokens.toLocaleString()} トークン`);
        }
        if (result.dropped_turns) {
            details.push(`古い会話を ${result.dropped_turns} 往復除外`);
        }
        setStatus(details.join(" · "));
    } catch (error) {
        setStatus(error.message, true);
    } finally {
        submit.disabled = false;
        keepHistory.disabled = false;
        clearHistory.disabled = historyMessages.length === 0;
        question.readOnly = false;
    }
});
