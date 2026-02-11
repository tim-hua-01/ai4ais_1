// Configuration
const DEFAULT_MODELS = [
    "openai/gpt-5.2",
    "anthropic/claude-4.6-opus",
    "anthropic/claude-4.5-opus",
    "zai/glm-4.7",
    "moonshotai/kimi-k2.5",
    "openrouter/google/gemini-3-pro-preview",
];

const AVAILABLE_MODELS = [
    "openai/gpt-5.2",
    "anthropic/claude-4.6-opus",
    "anthropic/claude-4.5-opus",
    "zai/glm-4.7",
    "moonshotai/kimi-k2.5",
    "openrouter/google/gemini-3-pro-preview",
];

// Application state
let panelStates = [];
let currentPanelCount = 6;
let globalRequestInProgress = false;
let globalSystemMessage = "";
let selectedPanelForSystemMessage = null;

// Initialize on page load
document.addEventListener("DOMContentLoaded", () => {
    const panelCountSelect = document.getElementById("panelCount");
    const initialCount = parseInt(panelCountSelect.value);
    initializePanels(initialCount);
    setupEventListeners();
});

function initializePanels(count = 6) {
    const panelsGrid = document.getElementById("panelsGrid");
    panelsGrid.innerHTML = "";
    panelStates = [];
    currentPanelCount = count;

    // Update grid class
    panelsGrid.className = `panels-grid grid-${count}`;

    // Create panels
    for (let i = 0; i < count; i++) {
        const model = DEFAULT_MODELS[i] || DEFAULT_MODELS[0];
        const panel = createPanel(i, model);
        panelsGrid.appendChild(panel);

        // Initialize panel state
        panelStates[i] = {
            model: model,
            messages: [],
            element: panel,
            chatArea: panel.querySelector(".chat-area"),
            input: panel.querySelector(".panel-input"),
            sendBtn: panel.querySelector(".panel-send-btn"),
            resetBtn: panel.querySelector(".panel-reset-btn"),
            modelSelect: panel.querySelector(".panel-model-select"),
            isRequesting: false,
            systemMessage: "",
        };

        // Setup panel event listeners
        panelStates[i].sendBtn.addEventListener("click", () =>
            sendToPanelMessage(i)
        );
        panelStates[i].input.addEventListener("keydown", (e) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                sendToPanelMessage(i);
            }
        });
        panelStates[i].modelSelect.addEventListener("change", (e) => {
            panelStates[i].model = e.target.value;
        });
        panelStates[i].resetBtn.addEventListener("click", () => {
            resetPanelChat(i);
        });
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
                    ${AVAILABLE_MODELS.map(
                        (m) =>
                            `<option value="${m}" ${m === model ? "selected" : ""}>${m}</option>`
                    )}
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

    // Open modal
    systemMessageBtn.addEventListener("click", () => {
        globalSystemMessageInput.value = globalSystemMessage;
        updatePanelSystemSelectDropdown();
        systemMessageModal.style.display = "flex";
    });

    // Close modal
    const closeModal = () => {
        saveSystemMessages();
        systemMessageModal.style.display = "none";
    };
    closeSystemMessageBtn.addEventListener("click", closeModal);
    closeSystemMessageBtnFooter.addEventListener("click", closeModal);

    // Close modal when clicking outside
    systemMessageModal.addEventListener("click", (e) => {
        if (e.target === systemMessageModal) {
            closeModal();
        }
    });

    // Update panel system message display when panel is selected
    panelSystemSelect.addEventListener("change", (e) => {
        selectedPanelForSystemMessage = parseInt(e.target.value);
        if (!isNaN(selectedPanelForSystemMessage)) {
            panelSystemMessageInput.value = panelStates[selectedPanelForSystemMessage].systemMessage;
        } else {
            panelSystemMessageInput.value = "";
        }
    });

    // Clear panel system message
    clearPanelSystemBtn.addEventListener("click", () => {
        if (!isNaN(selectedPanelForSystemMessage)) {
            panelStates[selectedPanelForSystemMessage].systemMessage = "";
            panelSystemMessageInput.value = "";
        }
    });

    // Setup main resize handle
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
    // Clear messages and chat display for a single panel
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
        option.textContent = `Panel ${i + 1} (${panelStates[i].model.split("/")[1] || panelStates[i].model})`;
        panelSystemSelect.appendChild(option);
    }

    panelSystemSelect.value = currentValue;
}

function saveSystemMessages() {
    const newGlobalSystemMessage = document.getElementById("globalSystemMessage").value;

    // If global system message changed, update all panels
    if (newGlobalSystemMessage !== globalSystemMessage) {
        globalSystemMessage = newGlobalSystemMessage;

        // Update or remove system message in all panels
        for (let i = 0; i < panelStates.length; i++) {
            // Remove existing system message if present
            if (panelStates[i].messages.length > 0 &&
                panelStates[i].messages[0].role === "system" &&
                !panelStates[i].systemMessage) {
                panelStates[i].messages.shift();
            }

            // Add new global system message if set
            if (globalSystemMessage && !panelStates[i].systemMessage) {
                panelStates[i].messages.unshift({
                    role: "system",
                    content: globalSystemMessage,
                });
            }
        }
    }

    // Update panel-specific system message
    if (!isNaN(selectedPanelForSystemMessage) && selectedPanelForSystemMessage !== null) {
        const newPanelSystemMessage = document.getElementById("panelSystemMessage").value;
        const panelIndex = selectedPanelForSystemMessage;

        if (newPanelSystemMessage !== panelStates[panelIndex].systemMessage) {
            panelStates[panelIndex].systemMessage = newPanelSystemMessage;

            // Remove existing system messages from this panel
            while (panelStates[panelIndex].messages.length > 0 &&
                   panelStates[panelIndex].messages[0].role === "system") {
                panelStates[panelIndex].messages.shift();
            }

            // Add panel-specific system message first
            if (newPanelSystemMessage) {
                panelStates[panelIndex].messages.unshift({
                    role: "system",
                    content: newPanelSystemMessage,
                });
            } else if (globalSystemMessage) {
                // Fall back to global if panel message is cleared
                panelStates[panelIndex].messages.unshift({
                    role: "system",
                    content: globalSystemMessage,
                });
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

    // Add message to all panels
    for (let i = 0; i < panelStates.length; i++) {
        panelStates[i].messages.push({
            role: "user",
            content: message,
        });
        displayMessage(i, "user", message);
    }

    globalInput.value = "";
    globalInput.focus();

    // Prepare request (system messages already in state.messages as first element)
    const panels = panelStates.map((state) => ({
        model: state.model,
        messages: state.messages,
        enabled: true,
    }));

    // Send to backend with streaming-like behavior
    await sendRequestStreaming(panels, true);
}

async function sendToPanelMessage(panelIndex) {
    if (panelStates[panelIndex].isRequesting) return;

    const state = panelStates[panelIndex];
    const message = state.input.value.trim();

    if (!message) {
        return;
    }

    // Add message to this panel only
    state.messages.push({
        role: "user",
        content: message,
    });
    displayMessage(panelIndex, "user", message);
    state.input.value = "";

    // Prepare request (only this panel enabled, system messages already in s.messages)
    const panels = panelStates.map((s, idx) => ({
        model: s.model,
        messages: s.messages,
        enabled: idx === panelIndex,
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
        // Send requests in parallel and display as they complete
        const requests = panels.map((panel, panelIndex) => {
            if (!panel.enabled || panelIndex >= panelStates.length) {
                return Promise.resolve();
            }

            return fetch("/api/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
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

                    if (result === null) {
                        return; // Panel disabled
                    }

                    // Validate result object
                    if (typeof result !== "object" || !("content" in result)) {
                        console.error(`Invalid result format for panel ${panelIndex}:`, result);
                        displayMessage(
                            panelIndex,
                            "assistant",
                            "Error: Invalid response from server",
                            0,
                            null
                        );
                        return;
                    }

                    const content = result.content;
                    const duration = result.duration || 0;
                    const thinking = result.thinking || null;

                    // Display message immediately as it arrives
                    if (content.startsWith("Error:")) {
                        displayMessage(panelIndex, "assistant", content, duration, thinking);
                    } else {
                        // Add to context for next message
                        panelStates[panelIndex].messages.push({
                            role: "assistant",
                            content: content,
                        });
                        displayMessage(
                            panelIndex,
                            "assistant",
                            content,
                            duration,
                            thinking
                        );
                    }
                })
                .catch((error) => {
                    console.error(`Error for panel ${panelIndex}:`, error);
                    displayMessage(
                        panelIndex,
                        "assistant",
                        `Error: ${error.message}`,
                        0,
                        null
                    );
                });
        });

        // Wait for all requests to complete
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
    // Validate inputs
    if (!panelStates[panelIndex]) {
        console.error(`Panel ${panelIndex} not found`);
        return;
    }

    const state = panelStates[panelIndex];

    if (!state.chatArea) {
        console.error(`Chat area not found for panel ${panelIndex}`);
        return;
    }

    // Validate content
    if (content === null || content === undefined) {
        console.error(`Invalid content for panel ${panelIndex}:`, content);
        content = "Error: Empty response from model";
    }

    if (typeof content !== "string") {
        content = String(content);
    }

    // Create message elements
    try {
        const messageDiv = document.createElement("div");
        messageDiv.className = `message ${role}`;

        // Add thinking container if thinking exists (BEFORE content)
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

            // Render thinking as markdown
            try {
                thinkingContent.innerHTML = marked.parse(thinking);
            } catch (e) {
                console.error("Error parsing thinking markdown:", e);
                thinkingContent.textContent = thinking;
            }

            thinkingContainer.appendChild(thinkingToggle);
            thinkingContainer.appendChild(thinkingContent);
            messageDiv.appendChild(thinkingContainer);

            // Add toggle functionality
            thinkingToggle.addEventListener("click", () => {
                thinkingContent.classList.toggle("open");
                toggleIcon.classList.toggle("open");
            });
        }

        // Add content bubble (after thinking)
        const bubble = document.createElement("div");
        bubble.className = "message-bubble";

        // Render content as markdown
        try {
            bubble.innerHTML = marked.parse(content);
        } catch (e) {
            console.error("Error parsing markdown:", e);
            bubble.textContent = content;
        }

        messageDiv.appendChild(bubble);

        // Add timing info for assistant messages
        if (duration !== null && role === "assistant") {
            const timingDiv = document.createElement("div");
            timingDiv.className = "message-timing";
            timingDiv.textContent = `${parseFloat(duration).toFixed(2)}s`;
            messageDiv.appendChild(timingDiv);
        }

        state.chatArea.appendChild(messageDiv);

        // Force reflow to ensure rendering happens immediately
        state.chatArea.offsetHeight;

        // Use requestAnimationFrame to ensure rendering on next frame
        requestAnimationFrame(() => {
            // Scroll to bottom
            state.chatArea.scrollTop = state.chatArea.scrollHeight;
            // Force another reflow
            state.chatArea.offsetHeight;
        });
    } catch (e) {
        console.error(`Error creating message element for panel ${panelIndex}:`, e);
    }
}
