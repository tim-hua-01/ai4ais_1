// =============================================================================
// Multi-model comparison panel — frontend
// =============================================================================
// The model catalog and UI defaults come from the backend (/api/models and
// /api/config), which are driven by config/models.yaml. Nothing about which
// models exist or their reasoning options is hardcoded here.
// =============================================================================

// Model catalog: [{id, label, backend, reasoning_effort, available_efforts, configured, ...}]
let AVAILABLE_MODELS = [];
let MODELS_BY_ID = {};
let DEFAULT_PANEL_MODELS = [];
let REASONING_EFFORT_OPTIONS = ["default"];
let DEFAULT_PANEL_COUNT = 6;

// Application state
let panelStates = [];
let currentPanelCount = 6;
let globalRequestInProgress = false;
let globalSystemMessage = "";
let selectedPanelForSystemMessage = null;

// Initialize on page load
document.addEventListener("DOMContentLoaded", async () => {
    await loadConfig();
    const panelCountSelect = document.getElementById("panelCount");
    panelCountSelect.value = String(DEFAULT_PANEL_COUNT);
    initializePanels(DEFAULT_PANEL_COUNT);
    setupEventListeners();
});

async function loadConfig() {
    try {
        const [modelsRes, configRes] = await Promise.all([
            fetch("/api/models"),
            fetch("/api/config"),
        ]);
        const modelsData = await modelsRes.json();
        const configData = await configRes.json();

        AVAILABLE_MODELS = modelsData.models || [];
        MODELS_BY_ID = {};
        AVAILABLE_MODELS.forEach((m) => (MODELS_BY_ID[m.id] = m));

        DEFAULT_PANEL_MODELS = configData.default_panel_models || AVAILABLE_MODELS.map((m) => m.id);
        REASONING_EFFORT_OPTIONS = configData.reasoning_effort_options || ["default"];
        DEFAULT_PANEL_COUNT = configData.panel_count || 6;
    } catch (e) {
        console.error("Failed to load config:", e);
        alert("Failed to load model configuration from server. Check the server logs.");
    }
}

function modelLabel(modelId) {
    const m = MODELS_BY_ID[modelId];
    return m ? m.label : modelId;
}

// Build the <option> list for a model dropdown, marking the unconfigured ones.
function modelOptionsHtml(selectedId) {
    return AVAILABLE_MODELS.map((m) => {
        const warn = m.configured ? "" : " — no API key";
        const selected = m.id === selectedId ? "selected" : "";
        return `<option value="${m.id}" ${selected}>${m.label}${warn}</option>`;
    }).join("");
}

// Build the reasoning-effort dropdown for a given model.
function effortOptionsHtml(modelId, selectedEffort) {
    const m = MODELS_BY_ID[modelId];
    let options = m && m.available_efforts ? m.available_efforts.slice() : REASONING_EFFORT_OPTIONS.slice();
    const sel = selectedEffort || "default";
    return options
        .map((e) => {
            const labelMap = { default: `default (${(m && m.reasoning_effort) || "none"})` };
            const label = labelMap[e] || e;
            return `<option value="${e}" ${e === sel ? "selected" : ""}>${label}</option>`;
        })
        .join("");
}

function initializePanels(count) {
    const panelsGrid = document.getElementById("panelsGrid");
    panelsGrid.innerHTML = "";
    panelStates = [];
    currentPanelCount = count;

    panelsGrid.className = `panels-grid grid-${count}`;

    const fallbackModel = AVAILABLE_MODELS.length ? AVAILABLE_MODELS[0].id : "";

    for (let i = 0; i < count; i++) {
        const model = DEFAULT_PANEL_MODELS[i] || DEFAULT_PANEL_MODELS[0] || fallbackModel;
        const panel = createPanel(i, model);
        panelsGrid.appendChild(panel);

        panelStates[i] = {
            model: model,
            reasoningEffort: "default",
            messages: [],
            element: panel,
            chatArea: panel.querySelector(".chat-area"),
            input: panel.querySelector(".panel-input"),
            sendBtn: panel.querySelector(".panel-send-btn"),
            resetBtn: panel.querySelector(".panel-reset-btn"),
            modelSelect: panel.querySelector(".panel-model-select"),
            effortSelect: panel.querySelector(".panel-effort-select"),
            isRequesting: false,
            systemMessage: "",
        };

        panelStates[i].sendBtn.addEventListener("click", () => sendToPanelMessage(i));
        panelStates[i].input.addEventListener("keydown", (e) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                sendToPanelMessage(i);
            }
        });
        panelStates[i].modelSelect.addEventListener("change", (e) => {
            panelStates[i].model = e.target.value;
            // Refresh the effort dropdown for the newly selected model.
            panelStates[i].reasoningEffort = "default";
            panelStates[i].effortSelect.innerHTML = effortOptionsHtml(e.target.value, "default");
        });
        panelStates[i].effortSelect.addEventListener("change", (e) => {
            panelStates[i].reasoningEffort = e.target.value;
        });
        panelStates[i].resetBtn.addEventListener("click", () => resetPanelChat(i));
    }
}

function createPanel(index, model) {
    const panel = document.createElement("div");
    panel.className = "panel";

    panel.innerHTML = `
        <div class="panel-header">
            <div class="panel-title-wrapper">
                <span class="panel-title-text" contenteditable="true">Model ${index + 1}</span>
                <select class="panel-model-select">
                    ${modelOptionsHtml(model)}
                </select>
                <select class="panel-effort-select" title="Reasoning effort">
                    ${effortOptionsHtml(model, "default")}
                </select>
            </div>
        </div>
        <div class="chat-area"></div>
        <div class="panel-footer">
            <div class="panel-input-container">
                <textarea
                    class="panel-input"
                    placeholder="Send to this model only... (Shift+Enter for newline)"
                    rows="2"
                ></textarea>
                <button class="btn btn-primary btn-sm panel-send-btn">Send</button>
                <button class="btn btn-sm panel-reset-btn" title="Clear this panel's chat">Reset</button>
            </div>
        </div>
    `;

    return panel;
}

function setupEventListeners() {
    const sendAllBtn = document.getElementById("sendAllBtn");
    const globalInput = document.getElementById("globalInput");
    const panelCountSelect = document.getElementById("panelCount");
    const newTabBtn = document.getElementById("newTabBtn");
    const resizeHandle = document.querySelector(".main-resize-handle");
    const panelsGrid = document.getElementById("panelsGrid");

    sendAllBtn.addEventListener("click", sendToAllModels);
    globalInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
            e.preventDefault();
            sendToAllModels();
        }
    });
    panelCountSelect.addEventListener("change", (e) => {
        initializePanels(parseInt(e.target.value));
    });
    newTabBtn.addEventListener("click", () => {
        window.open(window.location.href, "_blank");
    });

    // System Message modal
    const systemMessageBtn = document.getElementById("systemMessageBtn");
    const systemMessageModal = document.getElementById("systemMessageModal");
    const closeSystemMessageBtn = document.getElementById("closeSystemMessageBtn");
    const closeSystemMessageBtnFooter = document.getElementById("closeSystemMessageBtnFooter");
    const globalSystemMessageInput = document.getElementById("globalSystemMessage");
    const panelSystemSelect = document.getElementById("panelSystemSelect");
    const panelSystemMessageInput = document.getElementById("panelSystemMessage");
    const clearPanelSystemBtn = document.getElementById("clearPanelSystemBtn");

    systemMessageBtn.addEventListener("click", () => {
        globalSystemMessageInput.value = globalSystemMessage;
        updatePanelSystemSelectDropdown();
        systemMessageModal.style.display = "flex";
    });

    const closeModal = () => {
        saveSystemMessages();
        systemMessageModal.style.display = "none";
    };
    closeSystemMessageBtn.addEventListener("click", closeModal);
    closeSystemMessageBtnFooter.addEventListener("click", closeModal);

    systemMessageModal.addEventListener("click", (e) => {
        if (e.target === systemMessageModal) {
            closeModal();
        }
    });

    panelSystemSelect.addEventListener("change", (e) => {
        selectedPanelForSystemMessage = parseInt(e.target.value);
        if (!isNaN(selectedPanelForSystemMessage)) {
            panelSystemMessageInput.value = panelStates[selectedPanelForSystemMessage].systemMessage;
        } else {
            panelSystemMessageInput.value = "";
        }
    });

    clearPanelSystemBtn.addEventListener("click", () => {
        if (!isNaN(selectedPanelForSystemMessage)) {
            panelStates[selectedPanelForSystemMessage].systemMessage = "";
            panelSystemMessageInput.value = "";
        }
    });

    // Main resize handle
    let isResizing = false;
    let startY = 0;
    let startHeight = 0;

    resizeHandle.addEventListener("mousedown", (e) => {
        isResizing = true;
        startY = e.clientY;
        startHeight = panelsGrid.offsetHeight;
        document.body.style.cursor = "row-resize";
        document.body.style.userSelect = "none";
    });

    document.addEventListener("mousemove", (e) => {
        if (!isResizing) return;
        const deltaY = e.clientY - startY;
        const newHeight = Math.max(200, startHeight + deltaY);
        panelsGrid.style.height = newHeight + "px";
        panelsGrid.style.flex = "0 0 auto";
    });

    document.addEventListener("mouseup", () => {
        isResizing = false;
        document.body.style.cursor = "default";
        document.body.style.userSelect = "auto";
    });
}

function resetPanelChat(panelIndex) {
    panelStates[panelIndex].messages = [];
    panelStates[panelIndex].chatArea.innerHTML = "";
    panelStates[panelIndex].input.value = "";
}

function updatePanelSystemSelectDropdown() {
    const panelSystemSelect = document.getElementById("panelSystemSelect");
    const currentValue = panelSystemSelect.value;
    panelSystemSelect.innerHTML = '<option value="">Select a panel...</option>';

    for (let i = 0; i < panelStates.length; i++) {
        const option = document.createElement("option");
        option.value = i;
        option.textContent = `Panel ${i + 1} (${modelLabel(panelStates[i].model)})`;
        panelSystemSelect.appendChild(option);
    }

    panelSystemSelect.value = currentValue;
}

function saveSystemMessages() {
    const newGlobalSystemMessage = document.getElementById("globalSystemMessage").value;

    if (newGlobalSystemMessage !== globalSystemMessage) {
        globalSystemMessage = newGlobalSystemMessage;

        for (let i = 0; i < panelStates.length; i++) {
            if (
                panelStates[i].messages.length > 0 &&
                panelStates[i].messages[0].role === "system" &&
                !panelStates[i].systemMessage
            ) {
                panelStates[i].messages.shift();
            }

            if (globalSystemMessage && !panelStates[i].systemMessage) {
                panelStates[i].messages.unshift({ role: "system", content: globalSystemMessage });
            }
        }
    }

    if (!isNaN(selectedPanelForSystemMessage) && selectedPanelForSystemMessage !== null) {
        const newPanelSystemMessage = document.getElementById("panelSystemMessage").value;
        const panelIndex = selectedPanelForSystemMessage;

        if (newPanelSystemMessage !== panelStates[panelIndex].systemMessage) {
            panelStates[panelIndex].systemMessage = newPanelSystemMessage;

            while (
                panelStates[panelIndex].messages.length > 0 &&
                panelStates[panelIndex].messages[0].role === "system"
            ) {
                panelStates[panelIndex].messages.shift();
            }

            if (newPanelSystemMessage) {
                panelStates[panelIndex].messages.unshift({ role: "system", content: newPanelSystemMessage });
            } else if (globalSystemMessage) {
                panelStates[panelIndex].messages.unshift({ role: "system", content: globalSystemMessage });
            }
        }
    }
}

async function sendToAllModels() {
    if (globalRequestInProgress) return;

    const globalInput = document.getElementById("globalInput");
    const message = globalInput.value.trim();

    if (!message) {
        alert("Please enter a message");
        return;
    }

    for (let i = 0; i < panelStates.length; i++) {
        panelStates[i].messages.push({ role: "user", content: message });
        displayMessage(i, "user", message);
    }

    globalInput.value = "";
    globalInput.focus();

    const panels = panelStates.map((state) => ({
        model: state.model,
        messages: state.messages,
        enabled: true,
        reasoning_effort: state.reasoningEffort,
    }));

    await sendRequestStreaming(panels, true);
}

async function sendToPanelMessage(panelIndex) {
    if (panelStates[panelIndex].isRequesting) return;

    const state = panelStates[panelIndex];
    const message = state.input.value.trim();
    if (!message) return;

    state.messages.push({ role: "user", content: message });
    displayMessage(panelIndex, "user", message);
    state.input.value = "";

    const panels = panelStates.map((s, idx) => ({
        model: s.model,
        messages: s.messages,
        enabled: idx === panelIndex,
        reasoning_effort: s.reasoningEffort,
    }));

    await sendRequestStreaming(panels, false, panelIndex);
}

async function sendRequestStreaming(panels, isGlobal = false, panelIndex = null) {
    const sendAllBtn = document.getElementById("sendAllBtn");
    const status = document.getElementById("status");

    if (isGlobal) {
        globalRequestInProgress = true;
        sendAllBtn.disabled = true;
        status.textContent = "Sending requests to models...";
        status.classList.add("loading");
    } else if (panelIndex !== null) {
        panelStates[panelIndex].isRequesting = true;
        panelStates[panelIndex].sendBtn.disabled = true;
    }

    try {
        const requests = panels.map((panel, idx) => {
            if (!panel.enabled || idx >= panelStates.length) {
                return Promise.resolve();
            }

            return fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ panels: [panel] }),
            })
                .then((response) => {
                    if (!response.ok) {
                        throw new Error(`Server error: ${response.status}`);
                    }
                    return response.json();
                })
                .then((data) => {
                    if (!data.results || data.results.length === 0) {
                        throw new Error("Invalid response from server");
                    }

                    const result = data.results[0];
                    if (result === null) return;

                    if (typeof result !== "object" || !("content" in result)) {
                        console.error(`Invalid result format for panel ${idx}:`, result);
                        displayMessage(idx, "assistant", "Error: Invalid response from server", 0, null);
                        return;
                    }

                    const content = result.content;
                    const duration = result.duration || 0;
                    const thinking = result.thinking || null;

                    if (content.startsWith("Error:")) {
                        displayMessage(idx, "assistant", content, duration, thinking);
                    } else {
                        panelStates[idx].messages.push({ role: "assistant", content: content });
                        displayMessage(idx, "assistant", content, duration, thinking);
                    }
                })
                .catch((error) => {
                    console.error(`Error for panel ${idx}:`, error);
                    displayMessage(idx, "assistant", `Error: ${error.message}`, 0, null);
                });
        });

        await Promise.all(requests);

        if (isGlobal) {
            status.textContent = "Done!";
            status.classList.remove("loading");
            setTimeout(() => {
                status.textContent = "";
            }, 2000);
        }
    } catch (error) {
        if (isGlobal) {
            status.textContent = `Error: ${error.message}`;
            status.classList.remove("loading");
        }
        console.error("Error:", error);
    } finally {
        if (isGlobal) {
            globalRequestInProgress = false;
            sendAllBtn.disabled = false;
        } else if (panelIndex !== null) {
            panelStates[panelIndex].isRequesting = false;
            panelStates[panelIndex].sendBtn.disabled = false;
        }
    }
}

function displayMessage(panelIndex, role, content, duration = null, thinking = null) {
    if (!panelStates[panelIndex]) {
        console.error(`Panel ${panelIndex} not found`);
        return;
    }

    const state = panelStates[panelIndex];
    if (!state.chatArea) {
        console.error(`Chat area not found for panel ${panelIndex}`);
        return;
    }

    if (content === null || content === undefined) {
        console.error(`Invalid content for panel ${panelIndex}:`, content);
        content = "Error: Empty response from model";
    }
    if (typeof content !== "string") {
        content = String(content);
    }

    try {
        const messageDiv = document.createElement("div");
        messageDiv.className = `message ${role}`;

        if (thinking && role === "assistant") {
            const thinkingContainer = document.createElement("div");
            thinkingContainer.className = "thinking-container";

            const thinkingToggle = document.createElement("div");
            thinkingToggle.className = "thinking-toggle";

            const toggleIcon = document.createElement("span");
            toggleIcon.className = "thinking-toggle-icon";
            toggleIcon.textContent = "▶";

            const toggleLabel = document.createElement("span");
            toggleLabel.textContent = "Thinking (click to expand)";

            thinkingToggle.appendChild(toggleIcon);
            thinkingToggle.appendChild(toggleLabel);

            const thinkingContent = document.createElement("div");
            thinkingContent.className = "thinking-content";

            try {
                thinkingContent.innerHTML = marked.parse(thinking);
            } catch (e) {
                console.error("Error parsing thinking markdown:", e);
                thinkingContent.textContent = thinking;
            }

            thinkingContainer.appendChild(thinkingToggle);
            thinkingContainer.appendChild(thinkingContent);
            messageDiv.appendChild(thinkingContainer);

            thinkingToggle.addEventListener("click", () => {
                thinkingContent.classList.toggle("open");
                toggleIcon.classList.toggle("open");
            });
        }

        const bubble = document.createElement("div");
        bubble.className = "message-bubble";

        try {
            bubble.innerHTML = marked.parse(content);
        } catch (e) {
            console.error("Error parsing markdown:", e);
            bubble.textContent = content;
        }

        messageDiv.appendChild(bubble);

        if (duration !== null && role === "assistant") {
            const timingDiv = document.createElement("div");
            timingDiv.className = "message-timing";
            timingDiv.textContent = `${parseFloat(duration).toFixed(2)}s`;
            messageDiv.appendChild(timingDiv);
        }

        state.chatArea.appendChild(messageDiv);
        state.chatArea.offsetHeight;

        requestAnimationFrame(() => {
            state.chatArea.scrollTop = state.chatArea.scrollHeight;
            state.chatArea.offsetHeight;
        });
    } catch (e) {
        console.error(`Error creating message element for panel ${panelIndex}:`, e);
    }
}
