/**
 * static/js/app.js
 * ----------------
 * Frontend controller for the AI Voice Chatbot. Handles state management,
 * user events, REST API requests to Flask, and local browser voice capabilities.
 */

document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements
    const chatMessages = document.getElementById("chat-messages");
    const textInput = document.getElementById("text-input");
    const sendBtn = document.getElementById("send-btn");
    const micBtn = document.getElementById("mic-btn");
    const waveContainer = document.getElementById("wave-container");
    const statusDot = document.getElementById("status-dot");
    const statusText = document.getElementById("status-text");
    const settingsToggle = document.getElementById("settings-toggle");
    const settingsClose = document.getElementById("settings-close");
    const settingsDrawer = document.getElementById("settings-drawer");
    const resetChatBtn = document.getElementById("reset-chat-btn");

    // Setting inputs
    const aiProvider = document.getElementById("ai-provider");
    const audioMode = document.getElementById("audio-mode");
    const ttsEnabled = document.getElementById("tts-enabled");

    // App State Variables
    let isListening = false;
    let isSpeaking = false;
    let activeBrowserRecognition = null;
    let activeBrowserUtterance = null;
    let serverSettings = {
        ai_provider: "gemini",
        tts_enabled: true
    };

    // Initialize configuration settings on load
    fetchSettings();

    // Event Listeners
    settingsToggle.addEventListener("click", () => settingsDrawer.classList.add("open"));
    settingsClose.addEventListener("click", () => settingsDrawer.classList.remove("open"));

    textInput.addEventListener("input", () => {
        // Auto-grow height of text input
        textInput.style.height = "auto";
        textInput.style.height = (textInput.scrollHeight) + "px";

        // Enable/Disable send button glow
        if (textInput.value.trim().length > 0) {
            sendBtn.classList.add("active");
        } else {
            sendBtn.classList.remove("active");
        }
    });

    textInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    sendBtn.addEventListener("click", sendMessage);
    micBtn.addEventListener("click", toggleVoiceInput);
    resetChatBtn.addEventListener("click", resetConversation);

    // Sync UI setting changes to server
    aiProvider.addEventListener("change", updateSettings);
    ttsEnabled.addEventListener("change", updateSettings);
    audioMode.addEventListener("change", () => {
        console.log(`Audio mode changed to: ${audioMode.value}`);
        // If switching away from browser mode, cancel active speech
        if (audioMode.value !== "browser" && isSpeaking) {
            stopBrowserSpeech();
        }
    });

    // Main Status UI Updater
    function setStatus(state) {
        // Reset classes
        statusDot.className = "status-indicator";
        micBtn.classList.remove("listening");
        waveContainer.classList.remove("active");

        switch (state) {
            case "ready":
                statusDot.classList.add("online");
                statusText.textContent = "Ready to assist you";
                break;
            case "listening":
                statusDot.classList.add("listening");
                statusText.textContent = "Listening...";
                micBtn.classList.add("listening");
                waveContainer.classList.add("active");
                break;
            case "thinking":
                statusDot.classList.add("thinking");
                statusText.textContent = "Thinking...";
                waveContainer.classList.add("active");
                break;
            case "retrying":
                statusDot.classList.add("retrying");
                statusText.textContent = "Rate limited — retrying...";
                waveContainer.classList.add("active");
                break;
            case "speaking":
                statusDot.classList.add("speaking");
                statusText.textContent = "Speaking...";
                waveContainer.classList.add("active");
                break;
            case "error":
                statusDot.classList.add("online");
                statusText.textContent = "An error occurred";
                break;
        }
    }

    // Append standard text messages to UI
    function appendMessage(text, sender) {
        const messageDiv = document.createElement("div");
        messageDiv.className = `message ${sender}-message`;

        const messageContent = document.createElement("div");
        messageContent.className = "message-content";

        const textPara = document.createElement("p");
        textPara.textContent = text;

        messageContent.appendChild(textPara);
        messageDiv.appendChild(messageContent);
        chatMessages.appendChild(messageDiv);

        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Append a rich styled error banner with icon + detail message
    function appendError(errorMsg) {
        const existing = chatMessages.querySelector(".error-banner.transient");
        if (existing) existing.remove();

        const banner = document.createElement("div");
        banner.className = "error-banner transient";

        // Split on first space after an emoji to style it separately
        const icon = document.createElement("span");
        icon.className = "error-icon";
        // Try to extract leading emoji as icon
        const match = errorMsg.match(/^([\u{1F000}-\u{1FFFF}\u2600-\u27FF]\uFE0F?|[\u{1F300}-\u{1F9FF}]|❌|⏳|🔑|🚫|🌐|🎤|⏰|❓|💬)\s*/u);
        if (match) {
            icon.textContent = match[1];
            const detail = document.createElement("span");
            detail.className = "error-detail";
            detail.textContent = errorMsg.slice(match[0].length);
            banner.appendChild(icon);
            banner.appendChild(detail);
        } else {
            banner.textContent = errorMsg;
        }

        chatMessages.appendChild(banner);
        chatMessages.scrollTop = chatMessages.scrollHeight;

        // Auto-dismiss after 8 seconds
        setTimeout(() => banner.remove(), 8000);
    }

    // Handle Text Send
    async function sendMessage() {
        const text = textInput.value.trim();
        if (!text) return;

        // Reset text area height
        textInput.value = "";
        textInput.style.height = "auto";
        sendBtn.classList.remove("active");

        // Cancel browser speech if user speaks/types new request
        if (isSpeaking) {
            stopBrowserSpeech();
        }

        appendMessage(text, "user");
        setStatus("thinking");

        try {
            const response = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: text })
            });

            const data = await response.json();

            if (!response.ok) {
                if (data.error_type === "rate_limit") {
                    // The server already retried 3 times. Show a clear quota error.
                    appendError(data.error + "\n\nTip: Gemini free tier allows ~15 requests/minute. Wait 60s and try again.");
                } else {
                    appendError(data.error || "Failed to fetch response.");
                }
                setStatus("ready");
                return;
            }

            appendMessage(data.response, "bot");

            // Output Speech (TTS)
            if (ttsEnabled.checked) {
                speakText(data.response);
            } else {
                setStatus("ready");
            }
        } catch (error) {
            console.error("Chat error:", error);
            appendError(error.message);
            setStatus("error");
        }
    }

    // Voice Input Switch (Trigger STT)
    function toggleVoiceInput() {
        if (isListening) {
            // Stop listening
            if (audioMode.value === "browser" && activeBrowserRecognition) {
                activeBrowserRecognition.stop();
            }
            setStatus("ready");
            isListening = false;
        } else {
            // Cancel speech first
            if (isSpeaking) {
                stopBrowserSpeech();
            }

            // Start listening
            isListening = true;
            if (audioMode.value === "browser") {
                startBrowserSpeechToText();
            } else {
                startHostSpeechToText();
            }
        }
    }

    // --- Browser Native Speech-to-Text ---
    function startBrowserSpeechToText() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            appendMessage("Web Speech Recognition is not supported by your browser. Defaulting to Server/Host mode.", "system");
            audioMode.value = "host";
            startHostSpeechToText();
            return;
        }

        activeBrowserRecognition = new SpeechRecognition();
        activeBrowserRecognition.lang = serverSettings.recognition_language || "en-US";
        activeBrowserRecognition.interimResults = false;
        activeBrowserRecognition.maxAlternatives = 1;

        activeBrowserRecognition.onstart = () => {
            setStatus("listening");
        };

        activeBrowserRecognition.onerror = (e) => {
            console.error("Speech Recognition Error:", e.error);
            if (e.error === "no-speech") {
                appendError("⏰ No speech detected. Please try speaking again.");
            } else if (e.error === "not-allowed") {
                appendError("🔑 Microphone permission denied by browser. Enable mic access in your browser settings.");
            } else if (e.error === "network") {
                appendError("🌐 Network error during speech recognition. Check your internet connection.");
            } else {
                appendError(`🎤 Microphone error: ${e.error}`);
            }
            isListening = false;
            setStatus("ready");
        };

        activeBrowserRecognition.onend = () => {
            isListening = false;
            if (statusText.textContent === "Listening...") {
                setStatus("ready");
            }
        };

        activeBrowserRecognition.onresult = async (event) => {
            const transcript = event.results[0][0].transcript;
            appendMessage(transcript, "user");
            setStatus("thinking");

            try {
                // Send text to Gemini/OpenAI
                const response = await fetch("/api/chat", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ message: transcript })
                });

                const data = await response.json();

                if (!response.ok) {
                    throw new Error(data.error || "Failed to fetch response.");
                }

                appendMessage(data.response, "bot");

                if (ttsEnabled.checked) {
                    speakText(data.response);
                } else {
                    setStatus("ready");
                }
            } catch (err) {
                console.error(err);
                appendError(err.message);
                setStatus("error");
            }
        };

        activeBrowserRecognition.start();
    }

    // --- Host-side (Server-side) Speech-to-Text ---
    async function startHostSpeechToText() {
        setStatus("listening");
        try {
            const response = await fetch("/api/stt", { method: "POST" });
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || "Host recording failed.");
            }

            appendMessage(data.text, "user");
            setStatus("thinking");

            // Fetch AI Response
            const chatResponse = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: data.text })
            });

            const chatData = await chatResponse.json();

            if (!chatResponse.ok) {
                throw new Error(chatData.error || "Failed to fetch response.");
            }

            appendMessage(chatData.response, "bot");

            if (ttsEnabled.checked) {
                speakText(chatData.response);
            } else {
                setStatus("ready");
            }
        } catch (error) {
            console.error("Host STT error:", error);
            appendError(error.message);
            setStatus("error");
        } finally {
            isListening = false;
        }
    }

    // --- Text-To-Speech Route Selector ---
    function speakText(text) {
        if (audioMode.value === "browser") {
            speakBrowserText(text);
        } else {
            speakHostText(text);
        }
    }

    // --- Browser Native Text-To-Speech ---
    function speakBrowserText(text) {
        if (!("speechSynthesis" in window)) {
            appendMessage("Browser TTS not supported. Defaulting to Host TTS.", "system");
            speakHostText(text);
            return;
        }

        stopBrowserSpeech(); // Stop active speech

        isSpeaking = true;
        setStatus("speaking");

        activeBrowserUtterance = new SpeechSynthesisUtterance(text);
        activeBrowserUtterance.onend = () => {
            isSpeaking = false;
            setStatus("ready");
        };
        activeBrowserUtterance.onerror = (e) => {
            console.error("Browser TTS error:", e);
            isSpeaking = false;
            setStatus("ready");
        };

        window.speechSynthesis.speak(activeBrowserUtterance);
    }

    function stopBrowserSpeech() {
        if ("speechSynthesis" in window && window.speechSynthesis.speaking) {
            window.speechSynthesis.cancel();
        }
        isSpeaking = false;
    }

    // --- Host-side (Server-side) Text-To-Speech ---
    async function speakHostText(text) {
        setStatus("speaking");
        try {
            await fetch("/api/tts", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text: text })
            });
        } catch (error) {
            console.error("Host TTS failed:", error);
        } finally {
            setStatus("ready");
        }
    }

    // Get current configuration from backend
    async function fetchSettings() {
        try {
            const response = await fetch("/api/settings");
            serverSettings = await response.json();

            // Set UI selectors
            aiProvider.value = serverSettings.ai_provider;
            ttsEnabled.checked = serverSettings.tts_enabled;
        } catch (error) {
            console.error("Failed to fetch settings from backend:", error);
        }
    }

    // Update settings in backend
    async function updateSettings() {
        try {
            const response = await fetch("/api/settings", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    ai_provider: aiProvider.value,
                    tts_enabled: ttsEnabled.checked
                })
            });
            const data = await response.json();
            serverSettings = data;
        } catch (error) {
            console.error("Failed to update settings:", error);
        }
    }

    // Reset Chat Session History
    async function resetConversation() {
        if (!confirm("Are you sure you want to clear the conversation history? This will reset the AI memory.")) {
            return;
        }

        try {
            await fetch("/api/settings", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ reset_history: true })
            });

            // Clear visual chatbox
            chatMessages.innerHTML = `
                <div class="message system-message">
                    <div class="message-content">
                        <p>🧹 Conversation history cleared. AI memory reset.</p>
                    </div>
                </div>
            `;
            appendMessage("Welcome back! Speak or type to begin chatting.", "system");
            settingsDrawer.classList.remove("open");
        } catch (error) {
            console.error("Reset history error:", error);
        }
    }
});
