const messages = document.getElementById("messages");
const command = document.getElementById("command");
const send = document.getElementById("send");
const apiToken = document.getElementById("api-token");


function requestHeaders(includeContentType = false) {
    const headers = {};
    const token = apiToken.value.trim();
    if (token) {
        headers.Authorization = `Bearer ${token}`;
    }
    if (includeContentType) {
        headers["Content-Type"] = "application/json";
    }
    return headers;
}


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

            headers: requestHeaders(true),

            body: JSON.stringify({
                message: message
            })

        });

        const data = await response.json();

        if (!response.ok) {
            addMessage(
                "SYSTEM",
                data.error || `Request failed (${response.status}).`,
                "kairo"
            );
            return;
        }

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

    } catch {

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

        const response = await fetch("/api/status", {
            headers: requestHeaders()
        });

        const status = await response.json();
        if (!response.ok) {
            const connection = response.status === 401
                ? "AUTH REQUIRED"
                : response.status === 403
                    ? "FORBIDDEN"
                    : `ERROR ${response.status}`;
            document.getElementById("connection").textContent = connection;
            document.getElementById("system-status").textContent = connection;
            document.getElementById("system-card-status").textContent = connection;
            document.getElementById("system-dot").dataset.status = "OFFLINE";
            return;
        }

        const components = status.components || {};
        const core = components.core || {};
        const security = components.security || {};
        const runtime = components.runtime || {};
        const agents = components.agents || {};
        const model = components.model || {};

        document.getElementById("system-status").textContent =
            status.status || "UNKNOWN";
        document.getElementById("system-card-status").textContent =
            status.status || "UNKNOWN";
        document.getElementById("system-dot").dataset.status =
            status.status || "UNKNOWN";
        document.getElementById("core-status").textContent =
            status.core || core.core || "UNKNOWN";

        document.getElementById("security-status").textContent =
            security.status || "UNKNOWN";

        document.getElementById("model-status").textContent =
            model.status || "UNKNOWN";

        document.getElementById("runtime-status").textContent =
            runtime.status || "UNKNOWN";

        document.getElementById("agent-status").textContent =
            agents.status || "UNKNOWN";

        document.getElementById("footer-core-status").textContent =
            status.core || core.core || "UNKNOWN";
        document.getElementById("footer-security-status").textContent =
            security.status || "UNKNOWN";
        document.getElementById("footer-model-status").textContent =
            model.status || "UNKNOWN";

        document.getElementById("connection").textContent =
            "CONNECTED";

    } catch {

        document.getElementById("connection").textContent =
            "OFFLINE";
        document.getElementById("system-status").textContent = "OFFLINE";
        document.getElementById("system-card-status").textContent = "OFFLINE";
        document.getElementById("system-dot").dataset.status = "OFFLINE";
    }
}


send.addEventListener("click", sendMessage);


command.addEventListener("keydown", event => {

    if (event.key === "Enter") {
        sendMessage();
    }

});


loadStatus();
apiToken.addEventListener("change", loadStatus);