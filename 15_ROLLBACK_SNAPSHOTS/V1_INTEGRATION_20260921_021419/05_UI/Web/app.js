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


async function sendMessage() {

    const message = command.value.trim();

    if (!message) {
        return;
    }

    addMessage("YOU", message, "you");

    command.value = "";

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
            data.response || data.error,
            "kairo"
        );

    } catch (error) {

        addMessage(
            "SYSTEM",
            "Unable to communicate with KAIRO Core.",
            "kairo"
        );
    }
}


async function loadStatus() {

    try {

        const response = await fetch("/api/status");

        const status = await response.json();

        document.getElementById("core-status").textContent =
            status.core || "UNKNOWN";

        document.getElementById("security-status").textContent =
            status.security || "UNKNOWN";

        document.getElementById("mode-status").textContent =
            status.mode || "UNKNOWN";

        document.getElementById("version-status").textContent =
            status.version || "UNKNOWN";

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