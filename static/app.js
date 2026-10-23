document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements
    const btnModelDropdown = document.getElementById("btn-model-dropdown");
    const selectedModelText = document.getElementById("selected-model-text");
    const panelModelDropdown = document.getElementById("panel-model-dropdown");
    
    const btnOpenDocModal = document.getElementById("btn-open-doc-modal");
    const btnCloseDocModal = document.getElementById("btn-close-doc-modal");
    const modalDocSearch = document.getElementById("modal-doc-search");
    const inputSearchDoc = document.getElementById("input-search-doc");
    const docModalList = document.getElementById("doc-modal-list");
    const selectedDocText = document.getElementById("selected-doc-text");
    const activeDocName = document.getElementById("active-doc-name");

    const sessionList = document.getElementById("session-list");
    const chatMessages = document.getElementById("chat-messages");
    const welcomeScreen = document.getElementById("welcome-screen");
    const userInput = document.getElementById("user-input");
    const btnSend = document.getElementById("btn-send");
    const btnNewChat = document.getElementById("btn-new-chat");
    const btnWebToggle = document.getElementById("btn-web-toggle");

    // State Variables
    let currentSessionId = null;
    let selectedModelId = "qwen/qwen3.6-27b";
    let selectedDocPath = null;
    let isWebSearchActive = false;
    let documents = [];
    let models = [];

    // Initialize App
    init();

    async function init() {
        await loadModels();
        await loadDocuments();
        await loadSessions();
        setupEventListeners();
    }

    function setupEventListeners() {
        btnNewChat.addEventListener("click", handleNewChat);
        btnSend.addEventListener("click", handleSendMessage);
        
        userInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSendMessage();
            }
        });

        btnWebToggle.addEventListener("click", () => {
            isWebSearchActive = !isWebSearchActive;
            btnWebToggle.classList.toggle("active", isWebSearchActive);
        });

        // Model Dropdown Toggle
        btnModelDropdown.addEventListener("click", (e) => {
            e.stopPropagation();
            panelModelDropdown.classList.toggle("hidden");
            btnModelDropdown.parentElement.classList.toggle("open", !panelModelDropdown.classList.contains("hidden"));
        });

        // Close Dropdown when clicking outside
        document.addEventListener("click", () => {
            panelModelDropdown.classList.add("hidden");
            btnModelDropdown.parentElement.classList.remove("open");
        });

        // Document Search Modal Controls
        btnOpenDocModal.addEventListener("click", () => {
            modalDocSearch.classList.remove("hidden");
            inputSearchDoc.value = "";
            filterAndRenderDocModal("");
            setTimeout(() => inputSearchDoc.focus(), 100);
        });

        btnCloseDocModal.addEventListener("click", () => {
            modalDocSearch.classList.add("hidden");
        });

        modalDocSearch.addEventListener("click", (e) => {
            if (e.target === modalDocSearch) {
                modalDocSearch.classList.add("hidden");
            }
        });

        inputSearchDoc.addEventListener("input", (e) => {
            filterAndRenderDocModal(e.target.value.trim());
        });

        // Auto-expand textarea
        userInput.addEventListener("input", function() {
            this.style.height = "auto";
            this.style.height = (this.scrollHeight) + "px";
        });
    }

    async function loadModels() {
        try {
            const res = await fetch("/api/models");
            const data = await res.json();
            models = data.models || [];
            
            if (data.active_model) {
                selectedModelId = data.active_model;
            }

            renderModelDropdown();
        } catch (e) {
            console.error("Modeller yüklenemedi:", e);
        }
    }

    function renderModelDropdown() {
        panelModelDropdown.innerHTML = "";
        
        models.forEach(m => {
            const card = document.createElement("div");
            card.className = `model-option-card ${m.id === selectedModelId ? 'selected' : ''}`;
            card.innerHTML = `
                <div class="model-card-header">
                    <span class="model-card-title">${escapeHtml(m.name)}</span>
                    <span class="model-badge">${escapeHtml(m.badge)}</span>
                </div>
                <div class="model-card-desc">${escapeHtml(m.desc)}</div>
            `;

            card.addEventListener("click", () => {
                selectedModelId = m.id;
                selectedModelText.textContent = m.name;
                panelModelDropdown.classList.add("hidden");
                btnModelDropdown.parentElement.classList.remove("open");
                renderModelDropdown();
            });

            panelModelDropdown.appendChild(card);
        });

        const currentM = models.find(m => m.id === selectedModelId);
        if (currentM) {
            selectedModelText.textContent = currentM.name;
        }
    }

    async function loadDocuments() {
        try {
            const res = await fetch("/api/documents");
            const data = await res.json();
            documents = data.documents || [];

            selectedDocText.textContent = `Döküman Seçin (${documents.length} Belge)...`;
        } catch (e) {
            console.error("Dökümanlar yüklenemedi:", e);
        }
    }

    function filterAndRenderDocModal(query) {
        docModalList.innerHTML = "";

        // Her zaman en üste "Dokümansız Genel AI & Web Modu" seçeneğini ekle
        const genelItem = document.createElement("div");
        genelItem.className = "doc-card-item";
        genelItem.style.border = "1px solid var(--accent-primary)";
        genelItem.style.backgroundColor = "rgba(139, 92, 246, 0.1)";
        genelItem.innerHTML = `
            <div class="doc-card-left">
                <div class="doc-type-icon" style="background:linear-gradient(135deg, #8b5cf6, #6366f1); color:white;">
                    <i class="fa-solid fa-globe"></i>
                </div>
                <div class="doc-info">
                    <span class="doc-name" style="color:var(--accent-primary); font-weight:700;">🌐 Genel AI & Canlı Web Araması (Dokümansız Mod)</span>
                    <span class="doc-folder">Yerel döküman kullanmadan doğrudan Genel AI veya Web araması ile sohbet edin.</span>
                </div>
            </div>
            <i class="fa-solid fa-chevron-right" style="color:var(--accent-primary); font-size:12px;"></i>
        `;

        genelItem.addEventListener("click", () => {
            selectedDocPath = "__GENEL_AI__";
            selectedDocText.textContent = "🌐 Genel AI & Web Araması";
            activeDocName.textContent = "Genel AI & Canlı Web Modu";
            modalDocSearch.classList.add("hidden");
            createNewSession("Genel AI & Web Araması", "__GENEL_AI__");
        });

        docModalList.appendChild(genelItem);

        const queryLower = query.toLowerCase();
        const filtered = documents.filter(d => 
            d.name.toLowerCase().includes(queryLower) || 
            d.folder.toLowerCase().includes(queryLower)
        );

        if (filtered.length === 0 && !query) {
            return;
        }

        filtered.forEach(d => {
            const ext = d.name.split('.').pop().toLowerCase();
            let iconClass = "fa-file-pdf";
            let typeClass = "pdf";

            if (ext === "docx" || ext === "doc") {
                iconClass = "fa-file-word";
                typeClass = "docx";
            } else if (ext === "pptx" || ext === "ppt") {
                iconClass = "fa-file-powerpoint";
                typeClass = "pptx";
            }

            const item = document.createElement("div");
            item.className = "doc-card-item";
            item.innerHTML = `
                <div class="doc-card-left">
                    <div class="doc-type-icon ${typeClass}">
                        <i class="fa-solid ${iconClass}"></i>
                    </div>
                    <div class="doc-info">
                        <span class="doc-name" title="${escapeHtml(d.name)}">${escapeHtml(d.name)}</span>
                        <span class="doc-folder"><i class="fa-regular fa-folder"></i> ${escapeHtml(d.folder)}</span>
                    </div>
                </div>
                <i class="fa-solid fa-chevron-right" style="color:var(--text-muted); font-size:12px;"></i>
            `;

            item.addEventListener("click", () => {
                selectedDocPath = d.path;
                selectedDocText.textContent = d.name;
                activeDocName.textContent = d.name;
                modalDocSearch.classList.add("hidden");
                createNewSession(d.name, d.path);
            });

            docModalList.appendChild(item);
        });
    }

    async function loadSessions() {
        try {
            const res = await fetch("/api/sessions");
            const data = await res.json();
            const sessions = data.sessions || [];

            sessionList.innerHTML = "";
            if (sessions.length === 0) {
                sessionList.innerHTML = '<div style="font-size:12px; color:var(--text-muted); padding:8px;">Henüz sohbet yok.</div>';
                return;
            }

            sessions.forEach(s => {
                const item = document.createElement("div");
                item.className = `session-item ${s.id === currentSessionId ? 'active' : ''}`;
                item.innerHTML = `
                    <span class="session-title-text" title="${escapeHtml(s.title)}">${escapeHtml(s.title)}</span>
                    <button class="btn-delete-session" data-id="${s.id}" title="Sohbeti Sil">
                        <i class="fa-solid fa-trash-can"></i>
                    </button>
                `;

                item.addEventListener("click", (e) => {
                    if (!e.target.closest(".btn-delete-session")) {
                        openSession(s.id);
                    }
                });

                const btnDel = item.querySelector(".btn-delete-session");
                btnDel.addEventListener("click", async (e) => {
                    e.stopPropagation();
                    if (confirm("Bu sohbet oturumunu silmek istediğinize emin misiniz?")) {
                        await deleteSession(s.id);
                    }
                });

                sessionList.appendChild(item);
            });
        } catch (e) {
            console.error("Sohbet geçmişi yüklenemedi:", e);
        }
    }

    async function createNewSession(docName, docPath) {
        try {
            const res = await fetch("/api/sessions", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    doc_path: docPath,
                    model_name: selectedModelId,
                    title: `${docName} Sohbeti`
                })
            });
            const sessionData = await res.json();
            currentSessionId = sessionData.id;
            activeDocName.textContent = docName;
            
            await loadSessions();
            await openSession(currentSessionId);
        } catch (e) {
            console.error("Yeni oturum oluşturulamadı:", e);
        }
    }

    async function openSession(sessionId) {
        currentSessionId = sessionId;
        await loadSessions();
        
        try {
            const res = await fetch(`/api/sessions/${sessionId}`);
            const data = await res.json();
            const session = data.session;
            const messages = data.messages || [];

            activeDocName.textContent = session.doc_name;
            selectedDocText.textContent = session.doc_name;
            selectedModelId = session.model_name || selectedModelId;
            renderModelDropdown();

            welcomeScreen.style.display = "none";
            chatMessages.innerHTML = "";

            messages.forEach(msg => {
                renderMessageBubble(msg.role, msg.content, msg.context, msg.is_fallback);
            });

            scrollToBottom();
        } catch (e) {
            console.error("Oturum detayları yüklenemedi:", e);
        }
    }

    async function deleteSession(sessionId) {
        try {
            await fetch(`/api/sessions/${sessionId}`, { method: "DELETE" });
            if (currentSessionId === sessionId) {
                currentSessionId = null;
                chatMessages.innerHTML = "";
                welcomeScreen.style.display = "block";
                activeDocName.textContent = "Lütfen bir belge seçin";
                selectedDocText.textContent = "Döküman Seçin...";
            }
            await loadSessions();
        } catch (e) {
            console.error("Oturum silinemedi:", e);
        }
    }

    function handleNewChat() {
        if (selectedDocPath) {
            const docObj = documents.find(d => d.path === selectedDocPath);
            if (docObj) {
                createNewSession(docObj.name, docObj.path);
                return;
            }
        }
        currentSessionId = null;
        chatMessages.innerHTML = "";
        welcomeScreen.style.display = "block";
        activeDocName.textContent = "Lütfen bir belge seçin";
        selectedDocText.textContent = "Döküman Seçin...";
        loadSessions();
    }

    async function handleSendMessage() {
        const text = userInput.value.trim();
        if (!text) return;

        if (!currentSessionId) {
            if (selectedDocPath && selectedDocPath !== "__GENEL_AI__") {
                const docObj = documents.find(d => d.path === selectedDocPath);
                if (docObj) {
                    await createNewSession(docObj.name, docObj.path);
                } else {
                    await createNewSession("Genel AI & Web Araması", "__GENEL_AI__");
                }
            } else {
                await createNewSession("Genel AI & Web Araması", "__GENEL_AI__");
            }
        }

        welcomeScreen.style.display = "none";
        renderMessageBubble("user", text);
        userInput.value = "";
        userInput.style.height = "auto";
        scrollToBottom();

        const botBubble = createAssistantShell();
        const contentDiv = botBubble.querySelector(".message-content");

        try {
            const response = await fetch("/api/chat/stream", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    session_id: currentSessionId,
                    question: text,
                    model_name: selectedModelId,
                    use_web_search: isWebSearchActive
                })
            });

            const reader = response.body.getReader();
            const decoder = new TextDecoder("utf-8");
            let fullText = "";
            let buffer = "";
            let metaData = null;

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split("\n\n");
                buffer = lines.pop(); // Incomplete part remains in buffer

                for (let line of lines) {
                    const trimmedLine = line.trim();
                    if (trimmedLine.startsWith("data:")) {
                        const jsonStr = trimmedLine.replace(/^data:\s*/, "").trim();
                        if (!jsonStr) continue;

                        try {
                            const event = JSON.parse(jsonStr);
                            if (event.type === "meta") {
                                metaData = event;
                                if (event.is_fallback) {
                                    const existingBadge = contentDiv.querySelector(".fallback-badge");
                                    if (!existingBadge) {
                                        const badge = document.createElement("div");
                                        badge.className = "fallback-badge";
                                        badge.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> <span>Genel AI Bilgisi</span>';
                                        contentDiv.prepend(badge);
                                    }
                                }
                            } else if (event.type === "model_switched") {
                                const switchBadge = document.createElement("div");
                                switchBadge.className = "fallback-badge";
                                switchBadge.style.backgroundColor = "rgba(139, 92, 246, 0.15)";
                                switchBadge.style.color = "#a78bfa";
                                switchBadge.style.borderColor = "rgba(139, 92, 246, 0.4)";
                                switchBadge.innerHTML = `<i class="fa-solid fa-bolt"></i> <span>Otomatik Model Geçişi: ${escapeHtml(event.switched_model)} (${escapeHtml(event.reason)})</span>`;
                                contentDiv.prepend(switchBadge);
                            } else if (event.type === "text") {
                                fullText += event.content;
                                const splitResult = dusunce_ve_yaniti_ayir_js(fullText);
                                const displayAnswer = splitResult.answer || (splitResult.thinking ? "" : fullText);
                                
                                if (splitResult.thinking) {
                                    renderThinkingAccordionLive(contentDiv, splitResult.thinking);
                                }
                                
                                const parsedMarkdown = marked.parse(displayAnswer);
                                const existingBadge = contentDiv.querySelector(".fallback-badge");
                                const existingThinking = contentDiv.querySelector(".thinking-accordion");
                                
                                contentDiv.innerHTML = (existingBadge ? existingBadge.outerHTML : "") + 
                                                      (existingThinking ? existingThinking.outerHTML : "") + 
                                                      parsedMarkdown;
                                scrollToBottom();
                            } else if (event.type === "end") {
                                if (event.thinking) {
                                    renderThinkingAccordion(contentDiv, event.thinking);
                                }
                                if (metaData && metaData.context && metaData.context.length > 0) {
                                    renderCitations(contentDiv, metaData.context);
                                }
                                loadSessions();
                            }
                        } catch (err) {
                            console.error("JSON parse hatası:", err, "Veri:", jsonStr);
                        }
                    }
                }
            }
        } catch (e) {
            contentDiv.innerHTML = `<span style="color:#ef4444;">❌ Hata oluştu: ${e.message}</span>`;
        }
    }

    function createAssistantShell() {
        const row = document.createElement("div");
        row.className = "message-row";
        row.innerHTML = `
            <div class="message-avatar bot-avatar"><i class="fa-solid fa-robot"></i></div>
            <div class="message-content">
                <span style="color:var(--text-muted); font-size:12px;">Yanıt yazılıyor...</span>
            </div>
        `;
        chatMessages.appendChild(row);
        return row;
    }

    function renderMessageBubble(role, content, context = null, isFallback = false) {
        const row = document.createElement("div");
        row.className = "message-row";

        if (role === "user") {
            row.innerHTML = `
                <div class="message-avatar user-avatar"><i class="fa-solid fa-user"></i></div>
                <div class="message-content user-msg">${escapeHtml(content)}</div>
            `;
        } else {
            const fallbackHtml = isFallback ? '<div class="fallback-badge"><i class="fa-solid fa-triangle-exclamation"></i> <span>Genel AI Bilgisi</span></div>' : '';
            const parsedMd = marked.parse(content || "");
            
            row.innerHTML = `
                <div class="message-avatar bot-avatar"><i class="fa-solid fa-robot"></i></div>
                <div class="message-content">${fallbackHtml}${parsedMd}</div>
            `;

            if (context && context.length > 0) {
                renderCitations(row.querySelector(".message-content"), context);
            }
        }

        chatMessages.appendChild(row);
    }

    function renderCitations(container, context) {
        const accordion = document.createElement("div");
        accordion.className = "citation-accordion";
        
        const header = document.createElement("div");
        header.className = "citation-header";
        header.innerHTML = `
            <span><i class="fa-solid fa-quote-left"></i> Kullanılan Bağlamlar (${context.length} Parça)</span>
            <i class="fa-solid fa-chevron-down"></i>
        `;

        const body = document.createElement("div");
        body.className = "citation-body";
        
        context.forEach((c, idx) => {
            const item = document.createElement("div");
            item.style.marginBottom = "8px";
            item.innerHTML = `<strong>[Parça ${idx+1} - Sayfa ${c.page}]:</strong> ${escapeHtml(c.content)}`;
            body.appendChild(item);
        });

        header.addEventListener("click", () => {
            accordion.classList.toggle("open");
        });

        accordion.appendChild(header);
        accordion.appendChild(body);
        container.appendChild(accordion);
    }

    function renderThinkingAccordion(container, thinkingText) {
        if (!thinkingText || !thinkingText.trim()) return;

        const accordion = document.createElement("div");
        accordion.className = "thinking-accordion";

        const header = document.createElement("div");
        header.className = "thinking-header";
        header.innerHTML = `
            <span><i class="fa-solid fa-brain"></i> Düşünce Süreci (Thinking Process)</span>
            <i class="fa-solid fa-chevron-down arrow"></i>
        `;

        const body = document.createElement("div");
        body.className = "thinking-body";
        body.textContent = thinkingText;

        header.addEventListener("click", () => {
            accordion.classList.toggle("open");
        });

        accordion.appendChild(header);
        accordion.appendChild(body);
        container.prepend(accordion);
    }

    function dusunce_ve_yaniti_ayir_js(metin) {
        if (!metin) return { thinking: "", answer: "" };
        
        let thinking = "";
        let answer = metin;

        if (metin.includes("<think>")) {
            const parts = metin.split("</think>");
            if (parts.length > 1) {
                thinking = parts[0].replace("<think>", "").trim();
                answer = parts.slice(1).join("</think>").trim();
            } else {
                thinking = metin.replace("<think>", "").trim();
                answer = "";
            }
        } else if (metin.includes("Here's a thinking process:") || metin.includes("Analyze User Input:")) {
            const lines = metin.split("\n");
            let thinkingLines = [];
            let answerLines = [];
            let inThinking = true;

            for (let line of lines) {
                const lTrim = line.trim();
                if (["Here's a thinking process", "Analyze User Input", "Task:", "Check Constraints", "Draft Construction", "Evaluate Context", "Rule ", "Snippet ", "Excerpt ", "Identify Entities"].some(p => lTrim.startsWith(p))) {
                    inThinking = true;
                    thinkingLines.push(line);
                    continue;
                }
                if (inThinking) {
                    if (/^[A-ZÇĞİÖŞÜa-zçğıöşü0-9]/.test(lTrim) && !["Draft", "Constraint", "Prompt", "System", "Rule", "Snippet", "Excerpt", "Process", "Analyze"].some(k => lTrim.includes(k)) && !lTrim.endsWith(":")) {
                        inThinking = false;
                        answerLines.push(line);
                    } else {
                        thinkingLines.push(line);
                    }
                } else {
                    answerLines.push(line);
                }
            }
            thinking = thinkingLines.join("\n").trim();
            answer = answerLines.join("\n").trim();
        }

        return { thinking, answer };
    }

    function renderThinkingAccordionLive(container, thinkingText) {
        if (!thinkingText || !thinkingText.trim()) return;

        let accordion = container.querySelector(".thinking-accordion");
        if (!accordion) {
            accordion = document.createElement("div");
            accordion.className = "thinking-accordion";
            accordion.innerHTML = `
                <div class="thinking-header">
                    <span><i class="fa-solid fa-brain"></i> Düşünce Süreci (Thinking Process)</span>
                    <i class="fa-solid fa-chevron-down arrow"></i>
                </div>
                <div class="thinking-body"></div>
            `;
            const header = accordion.querySelector(".thinking-header");
            header.addEventListener("click", () => {
                accordion.classList.toggle("open");
            });
            container.prepend(accordion);
        }

        const body = accordion.querySelector(".thinking-body");
        body.textContent = thinkingText;
    }

    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function escapeHtml(text) {
        if (!text) return "";
        return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }
});
