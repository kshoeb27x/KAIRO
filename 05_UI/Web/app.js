const messages = document.getElementById("messages");
const command = document.getElementById("command");
const send = document.getElementById("send");


function addMessage(sender, text, type) {

    const wrapper = document.createElement("div");

    wrapper.className = `message ${type}`;

    wrapper.innerHTML = `
        <div class="message-name">${sender}</div>
        <div>${escapeHtml(text)}</div>
    `;

    messages.appendChild(wrapper);

    messages.scrollTop = messages.scrollHeight;
}


function escapeHtml(text) {

    const div = document.createElement("div");

    div.textContent = text;

    return div.innerHTML;
}


function formatResponse(data) {

    if (typeof data === "string") {
        return data;
    }

    if (data === null || data === undefined) {
        return "No response.";
    }

    try {
        return JSON.stringify(data, null, 2);
    } catch {
        return String(data);
    }
}


function setBusyState(isBusy) {
    send.disabled = isBusy;
    command.disabled = isBusy;
    send.textContent = isBusy ? "SENDING..." : "SEND";
}


async function sendMessage() {

    const message = command.value.trim();

    if (!message) {
        return;
    }

    addMessage("YOU", message, "you");

    command.value = "";
    setBusyState(true);

    try {

        const response = await fetch("/api/chat", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                message: message
            })

        });

        const data = await response.json();

        if (data.response === "__EXIT__") {

            addMessage(
                "KAIRO",
                "Shutdown command received.",
                "kairo"
            );

            return;
        }

        addMessage(
            "KAIRO",
            formatResponse(data.response ?? data.error ?? "No response."),
            "kairo"
        );

    } catch (error) {

        addMessage(
            "SYSTEM",
            "Unable to communicate with KAIRO Core.",
            "kairo"
        );
    } finally {
        setBusyState(false);
        command.focus();
    }
}


async function loadStatus() {

    try {

        const response = await fetch("/api/status");

        const status = await response.json();
        const components = status.components || {};
        const core = components.core || {};
        const security = components.security || {};

        document.getElementById("core-status").textContent =
            status.core || core.core || "UNKNOWN";

        document.getElementById("security-status").textContent =
            status.security || security.status || "UNKNOWN";

        document.getElementById("mode-status").textContent =
            status.mode || core.mode || "UNKNOWN";

        document.getElementById("version-status").textContent =
            status.version || core.version || "UNKNOWN";

        document.getElementById("connection").textContent =
            "CONNECTED";

    } catch {

        document.getElementById("connection").textContent =
            "OFFLINE";
    }
}


send.addEventListener("click", sendMessage);


command.addEventListener("keydown", event => {

    if (event.key === "Enter") {
        sendMessage();
    }

});


loadStatus();