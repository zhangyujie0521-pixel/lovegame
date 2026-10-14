// ASTERIA 乙游客户端主交互逻辑
let gameState = null;
let activePrivateCharId = null;
let currentChatSubtab = 'group'; // 'group' or 'private'

document.addEventListener("DOMContentLoaded", () => {
    initApp();
});

async function initApp() {
    setupNavListeners();
    await fetchLLMStatus();
    await fetchGameState();
    if (!gameState || !gameState.is_active) {
        showGenesisModal();
    } else {
        renderAll();
    }
}

// 底部导航栏切换
function setupNavListeners() {
    document.querySelectorAll(".nav-item").forEach(item => {
        item.addEventListener("click", () => {
            document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));
            document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));

            item.classList.add("active");
            const target = item.getAttribute("data-tab");
            const pane = document.getElementById(target);
            if (pane) pane.classList.add("active");

            // 切换到故事时刷新剧情
            if (target === "tab-story") {
                loadCurrentStory();
            }
        });
    });
}

// 获取游戏全局状态
async function fetchGameState() {
    try {
        const res = await fetch("/api/state");
        gameState = await res.json();
        return gameState;
    } catch (e) {
        console.error("加载状态失败", e);
    }
}

// 渲染所有视图
function renderAll() {
    if (!gameState) return;

    // 1. 检查黑化模式
    if (gameState.is_total_blackened) {
        document.body.classList.add("blackened-mode");
    } else {
        document.body.classList.remove("blackened-mode");
    }

    // 2. 顶部状态栏
    document.getElementById("player-name-display").textContent = gameState.player_name;
    document.getElementById("player-career-display").textContent = gameState.career ? gameState.career.name : "制作人";
    
    // 危险度药丸
    const dangerPill = document.getElementById("danger-pill");
    const count = gameState.dating_count;
    dangerPill.innerHTML = `<span>❤️ 秘恋 ${count}/3</span>`;
    if (gameState.is_total_blackened) {
        dangerPill.className = "danger-meter-pill danger-high";
        dangerPill.innerHTML = `<span>💥 全员黑化中</span>`;
    } else if (count >= 3) {
        dangerPill.className = "danger-meter-pill danger-high";
    } else {
        dangerPill.className = "danger-meter-pill";
    }

    // 3. 渲染各个模块
    renderRoster();
    loadGroupChat();
    renderPrivateMembersSlider();
}

// ==================== 创角开局模态框 (Genesis) ====================
async function showGenesisModal() {
    const modal = document.getElementById("genesis-modal");
    modal.style.display = "flex";

    // 加载职业列表
    try {
        const metaRes = await fetch("/api/meta");
        const meta = await metaRes.json();
        const container = document.getElementById("career-options-container");
        container.innerHTML = "";
        meta.careers.forEach((c, idx) => {
            const div = document.createElement("div");
            div.className = `career-option ${idx === 0 ? 'selected' : ''}`;
            div.dataset.id = c.id;
            div.innerHTML = `
                <div class="career-title">${c.name} · <span style="color:var(--accent-gold);font-size:11px;">${c.tag}</span></div>
                <div class="career-desc">${c.desc}</div>
            `;
            div.onclick = () => {
                document.querySelectorAll(".career-option").forEach(el => el.classList.remove("selected"));
                div.classList.add("selected");
            };
            container.appendChild(div);
        });
    } catch (e) {
        console.error(e);
    }
}

async function submitGenesis() {
    const nameInput = document.getElementById("genesis-name").value.trim() || "林初";
    const selectedCareerEl = document.querySelector(".career-option.selected");
    const careerId = selectedCareerEl ? selectedCareerEl.dataset.id : "stylist";

    const btn = document.getElementById("btn-start-genesis");
    btn.textContent = "🎲 命运轮盘旋转中...抽选中...";
    btn.disabled = true;

    try {
        const res = await fetch("/api/new_game", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ player_name: nameInput, career_id: careerId })
        });
        const data = await res.json();
        if (data.success) {
            gameState = data.state;
            document.getElementById("genesis-modal").style.display = "none";
            btn.textContent = "启动命运轮盘 (从0开始)";
            btn.disabled = false;

            // 弹出宿命揭晓动画提醒
            alert(`【命运揭晓】\n👑 你的亲哥哥是：${gameState.brother_name}！\n🤫 12位队友中，有一位暗恋者已埋下心动宿命！\n其余11位成员初始为 0 好感，请通过剧情展开攻略！`);
            renderAll();
        }
    } catch (e) {
        alert("启动失败，请检查网络！");
        btn.disabled = false;
    }
}

// ==================== 13人花名册 (Roster) ====================
function renderRoster() {
    const list = document.getElementById("roster-list");
    if (!list || !gameState.members) return;

    list.innerHTML = "";
    gameState.members.forEach(m => {
        const isBrother = (m.id === gameState.brother_id);
        const isCrush = (m.id === gameState.crush_id);
        const isDating = m.is_dating;

        let roleTagClass = "tag-member";
        let roleText = "队友 (0好感)";
        if (isBrother) {
            roleTagClass = "tag-brother";
            roleText = "亲哥哥 (守护者)";
        } else if (isDating) {
            roleTagClass = "tag-dating";
            roleText = "秘密地下恋人";
        } else if (isCrush) {
            roleTagClass = "tag-crush";
            roleText = "隐藏暗恋者";
        }

        const card = document.createElement("div");
        card.className = `character-card ${isBrother ? 'is-brother' : ''} ${isCrush ? 'is-crush' : ''} ${isDating ? 'is-dating' : ''}`;
        card.innerHTML = `
            <div class="card-avatar-box">
                <div class="card-avatar" style="background:${m.avatar_color}">
                    ${m.name.charAt(0)}
                </div>
                <div class="card-age-tag">#${m.age_rank} ${m.age_title}</div>
            </div>
            <div class="card-info">
                <div class="card-name-row">
                    <span class="card-name">${m.name}</span>
                    <span class="card-identity-tag ${roleTagClass}">${roleText}</span>
                </div>
                <div class="card-unit">${m.unit} · ${m.mbti} · ${m.korean_hint}</div>
                <div class="aff-bar-wrapper">
                    <div class="aff-bar-fill" style="width: ${m.affinity}%"></div>
                </div>
                <div style="font-size:11px;color:var(--text-muted);display:flex;justify-content:space-between;margin-bottom:6px;">
                    <span>好感羁绊: <b style="color:var(--accent-gold);">${m.affinity}/100</b></span>
                    <span>${m.is_blackened ? '💥 已黑化' : (m.affinity >= 60 ? '🔥 极度暧昧' : (m.affinity >= 20 ? '💓 心动萌芽' : '❄️ 熟人'))}</span>
                </div>
                <div class="card-actions">
                    <button class="btn-mini" onclick="openPrivateChatWith('${m.id}')">💬 私聊</button>
                    ${!isBrother && !isDating ? `<button class="btn-mini" style="border-color:var(--accent-pink)" onclick="startDatingQuick('${m.id}')">💖 确立秘恋</button>` : ''}
                    ${isBrother ? `<span style="font-size:10px;color:#3498db;margin-left:4px;">门禁监视中</span>` : ''}
                </div>
            </div>
        `;
        list.appendChild(card);
    });
}

// 快速确立交往（测试/达成）
async function startDatingQuick(charId) {
    try {
        const res = await fetch("/api/dating/toggle", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ char_id: charId })
        });
        const data = await res.json();
        if (data.success) {
            await fetchGameState();
            renderAll();
            if (data.is_blackened) {
                alert("🚨【灾难级暴雷】交往人数达到 4 人！全团黑化剧情彻底爆发！所有人理智全无！");
            } else {
                alert(`💖 已成功与 ${data.char_name} 确立秘密恋爱关系！当前地下秘密交往：${data.dating_count}/3 人。切记千万别让其他人发现！`);
            }
        } else {
            alert(data.message);
        }
    } catch (e) {
        console.error(e);
    }
}

// ==================== 手机通讯系统 (Phone & Chat) ====================
function switchChatSubtab(type) {
    currentChatSubtab = type;
    document.querySelectorAll(".subtab-btn").forEach(btn => btn.classList.remove("active"));
    if (type === "group") {
        document.getElementById("btn-subtab-group").classList.add("active");
        document.getElementById("group-chat-view").style.display = "flex";
        document.getElementById("private-chat-view").style.display = "none";
        loadGroupChat();
    } else {
        document.getElementById("btn-subtab-private").classList.add("active");
        document.getElementById("group-chat-view").style.display = "none";
        document.getElementById("private-chat-view").style.display = "flex";
        if (!activePrivateCharId && gameState.members && gameState.members.length > 0) {
            // 默认选暗恋者或第一个非哥哥
            activePrivateCharId = gameState.crush_id || gameState.members[0].id;
        }
        loadPrivateChat(activePrivateCharId);
    }
}

async function loadGroupChat() {
    try {
        const res = await fetch("/api/chat/group");
        const data = await res.json();
        const container = document.getElementById("group-messages-box");
        container.innerHTML = "";

        data.messages.forEach(m => {
            const isMine = (m.sender_id === "player");
            const div = document.createElement("div");
            div.className = `message-bubble ${isMine ? 'mine' : 'other'}`;

            let roleTag = "";
            if (m.sender_id === gameState.brother_id) {
                roleTag = `<span class="msg-tag-brother">亲哥</span>`;
            } else if (m.sender_id === gameState.crush_id) {
                roleTag = `<span class="msg-tag-crush">暗恋者</span>`;
            } else if (gameState.dating_list.includes(m.sender_id)) {
                roleTag = `<span class="msg-tag-dating">秘密男友</span>`;
            }

            div.innerHTML = `
                ${!isMine ? `<div class="msg-sender">${m.sender_name} ${roleTag}</div>` : ''}
                <div class="msg-body">${m.text}</div>
            `;
            container.appendChild(div);
        });
        container.scrollTop = container.scrollHeight;
    } catch (e) {
        console.error(e);
    }
}

async function sendGroupMessage() {
    const input = document.getElementById("group-input");
    const text = input.value.trim();
    if (!text) return;

    input.value = "";

    // 立即在界面上插入用户的消息，以及正在输入中的提示气泡
    const container = document.getElementById("group-messages-box");
    const userDiv = document.createElement("div");
    userDiv.className = "message-bubble mine";
    userDiv.innerHTML = `<div class="msg-body">${text}</div>`;
    container.appendChild(userDiv);

    const typingDiv = document.createElement("div");
    typingDiv.className = "message-bubble other";
    typingDiv.id = "group-typing-indicator";
    typingDiv.innerHTML = `
        <div class="msg-sender" style="color:var(--accent-gold);">ASTERIA 成员们</div>
        <div class="msg-body"><span class="typing-dots"><span></span><span></span><span></span></span> 正在群里输入...</div>
    `;
    container.appendChild(typingDiv);
    container.scrollTop = container.scrollHeight;

    try {
        const res = await fetch("/api/chat/group/send", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text })
        });
        const data = await res.json();
        if (data.success) {
            loadGroupChat();
        }
    } catch (e) {
        console.error(e);
        if (typingDiv) typingDiv.remove();
    }
}

function renderPrivateMembersSlider() {
    const slider = document.getElementById("private-slider");
    if (!slider || !gameState.members) return;

    slider.innerHTML = "";
    gameState.members.forEach(m => {
        const isSelected = (m.id === activePrivateCharId);
        const div = document.createElement("div");
        div.className = `member-chip ${isSelected ? 'selected' : ''}`;
        div.onclick = () => {
            activePrivateCharId = m.id;
            renderPrivateMembersSlider();
            loadPrivateChat(m.id);
        };
        div.innerHTML = `
            <div class="chip-avatar" style="background:${m.avatar_color}">${m.name.charAt(0)}</div>
            <div class="chip-name">${m.name}</div>
        `;
        slider.appendChild(div);
    });
}

function openPrivateChatWith(charId) {
    // 切换到聊天 Tab
    document.querySelector('[data-tab="tab-chat"]').click();
    activePrivateCharId = charId;
    switchChatSubtab("private");
    renderPrivateMembersSlider();
}

async function loadPrivateChat(charId) {
    if (!charId) return;
    try {
        const res = await fetch(`/api/chat/private/${charId}`);
        const data = await res.json();
        const container = document.getElementById("private-messages-box");
        container.innerHTML = "";

        const char = data.character;
        document.getElementById("private-chat-title").textContent = `与 ${char.name} 的私密会话 (${char.affinity}/100)`;

        if (data.history.length === 0) {
            container.innerHTML = `
                <div style="text-align:center;color:var(--text-muted);font-size:12px;margin:auto;">
                    这里是与 ${char.name} 的私聊。<br>发送第一条消息打破沉寂吧……
                </div>
            `;
        } else {
            data.history.forEach(m => {
                const isMine = (m.sender === "player");
                const div = document.createElement("div");
                div.className = `message-bubble ${isMine ? 'mine' : 'other'}`;
                div.innerHTML = `
                    ${!isMine ? `<div class="msg-sender">${char.name}</div>` : ''}
                    <div class="msg-body">${m.text}</div>
                `;
                container.appendChild(div);
            });
            container.scrollTop = container.scrollHeight;
        }
    } catch (e) {
        console.error(e);
    }
}

async function sendPrivateMessage() {
    const input = document.getElementById("private-input");
    const text = input.value.trim();
    if (!text || !activePrivateCharId) return;

    input.value = "";

    // 立即显示玩家消息与“对方正在输入…”
    const container = document.getElementById("private-messages-box");
    const userDiv = document.createElement("div");
    userDiv.className = "message-bubble mine";
    userDiv.innerHTML = `<div class="msg-body">${text}</div>`;
    container.appendChild(userDiv);

    const typingDiv = document.createElement("div");
    typingDiv.className = "message-bubble other";
    typingDiv.id = "private-typing-indicator";
    typingDiv.innerHTML = `
        <div class="msg-body"><span class="typing-dots"><span></span><span></span><span></span></span> 正在敲字...</div>
    `;
    container.appendChild(typingDiv);
    container.scrollTop = container.scrollHeight;

    try {
        const res = await fetch("/api/chat/private/send", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ char_id: activePrivateCharId, text })
        });
        const data = await res.json();
        if (data.success) {
            loadPrivateChat(activePrivateCharId);
            await fetchGameState();
            renderRoster();
        }
    } catch (e) {
        console.error(e);
        if (typingDiv) typingDiv.remove();
    }
}

// ==================== 视觉小说剧场 (Story) ====================
async function loadCurrentStory() {
    try {
        const res = await fetch("/api/story/current");
        const data = await res.json();
        const ch = data.chapter;

        document.getElementById("story-chapter-title").textContent = ch.title;
        document.getElementById("story-chapter-desc").textContent = ch.desc;

        const vp = document.getElementById("story-viewport");
        vp.innerHTML = "";

        ch.dialogues.forEach(d => {
            const div = document.createElement("div");
            div.className = "story-bubble";
            div.innerHTML = `
                <div class="speaker-name">${d.speaker}</div>
                <div class="dialogue-text">${d.text}</div>
            `;
            vp.appendChild(div);
        });

        // 选项渲染
        const choicesContainer = document.getElementById("story-choices-container");
        choicesContainer.innerHTML = "";

        // 如果满足暗恋者暴雨夜上位剧情
        if (data.can_trigger_usurper && data.usurper_event) {
            const ue = data.usurper_event;
            const alertBox = document.createElement("div");
            alertBox.style = "background:rgba(231,76,60,0.2);border:1px solid #e74c3c;border-radius:12px;padding:10px;margin-bottom:8px;font-size:12px;";
            alertBox.innerHTML = `<b>⚡【特殊事件触发】${ue.title}</b><p style="margin-top:4px;">${ue.desc}</p>`;
            choicesContainer.appendChild(alertBox);

            ue.choices.forEach(c => {
                const btn = document.createElement("button");
                btn.className = "choice-btn";
                btn.style.borderColor = "#e74c3c";
                btn.innerHTML = `<span>${c.text}</span> <span>➡️</span>`;
                btn.onclick = () => submitUsurperChoice(c.id);
                choicesContainer.appendChild(btn);
            });
            return;
        }

        // 普通主线选择
        ch.choices.forEach((c, idx) => {
            const btn = document.createElement("button");
            btn.className = "choice-btn";
            btn.innerHTML = `<span>${c.text}</span> <span>✨</span>`;
            btn.onclick = () => submitStoryChoice(ch.id, idx);
            choicesContainer.appendChild(btn);
        });

    } catch (e) {
        console.error(e);
    }
}

async function submitStoryChoice(chapterId, choiceIndex) {
    try {
        const res = await fetch("/api/story/choice", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ chapter_id: chapterId, choice_index: choiceIndex })
        });
        const data = await res.json();
        if (data.success) {
            await fetchGameState();
            renderAll();
            loadCurrentStory();
        }
    } catch (e) {
        console.error(e);
    }
}

async function submitUsurperChoice(action) {
    try {
        const res = await fetch("/api/usurper", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action })
        });
        const data = await res.json();
        alert(data.msg);
        await fetchGameState();
        renderAll();
        loadCurrentStory();
    } catch (e) {
        console.error(e);
    }
}

// ==================== 抽卡神殿 (Gacha) ====================
async function drawGachaCard() {
    const btn = document.getElementById("btn-draw-card");
    btn.disabled = true;
    btn.textContent = "祈愿中...召唤命运星芒...";

    try {
        const res = await fetch("/api/gacha/draw", { method: "POST" });
        const data = await res.json();
        if (data.success) {
            const card = data.card;
            const resBox = document.getElementById("gacha-result-box");
            resBox.innerHTML = `
                <div class="card-display-box">
                    <span class="card-tier-badge">${card.tier}</span>
                    <div style="text-align:center;">
                        <div class="card-title-lg">${card.title}</div>
                        <div class="card-owner">${card.char_name} · ${card.scene}</div>
                    </div>
                    <div class="card-story-snippet">
                        <b>【专属回忆】</b><br>${card.story_preview}
                    </div>
                </div>
            `;
            await fetchGameState();
            renderAll();
        }
    } catch (e) {
        console.error(e);
    } finally {
        btn.disabled = false;
        btn.textContent = "✨ 注入星芒·单抽祈愿";
    }
}

// ==================== DeepSeek 大模型管理面板 ====================
let llmStatus = { is_configured: false, model: "deepseek-chat", api_base: "https://api.deepseek.com", masked_key: "" };

async function fetchLLMStatus() {
    try {
        const res = await fetch("/api/llm/status");
        llmStatus = await res.json();
        updateLLMUI();
    } catch (e) {
        console.error("获取 LLM 状态异常:", e);
    }
}

function updateLLMUI() {
    const pill = document.getElementById("btn-open-llm");
    const label = document.getElementById("ai-status-label");
    const statusBox = document.getElementById("llm-status-box");

    if (llmStatus.is_configured) {
        if (pill) pill.classList.add("active");
        if (label) label.textContent = `🤖 ${llmStatus.model || 'DeepSeek'}`;
        if (statusBox) {
            statusBox.innerHTML = `
                <div style="color:#2ecc71;font-weight:600;margin-bottom:2px;">● DeepSeek 已激活 (即时灵魂推拉开启)</div>
                <div>已配置密钥: <b>${llmStatus.masked_key}</b></div>
                <div>当前模型: <code>${llmStatus.model}</code></div>
            `;
        }
    } else {
        if (pill) pill.classList.remove("active");
        if (label) label.textContent = "🤖 DeepSeek (未配置)";
        if (statusBox) {
            statusBox.innerHTML = `
                <div style="color:#e67e22;font-weight:600;margin-bottom:2px;">○ 当前处于本地精修台词保底模式</div>
                <div>填入 DeepSeek API Key 即可为 13 位男主注入即时拟真灵魂与动态修罗场推拉。</div>
            `;
        }
    }
}

function openLLMModal() {
    const modal = document.getElementById("llm-modal");
    if (!modal) return;
    modal.style.display = "flex";
    fetchLLMStatus();
    if (llmStatus.model) {
        document.getElementById("llm-model-select").value = llmStatus.model;
    }
    if (llmStatus.api_base) {
        document.getElementById("llm-api-base").value = llmStatus.api_base;
    }
}

function closeLLMModal() {
    const modal = document.getElementById("llm-modal");
    if (modal) modal.style.display = "none";
}

function toggleKeyVisibility() {
    const input = document.getElementById("llm-api-key");
    input.type = input.type === "password" ? "text" : "password";
}

async function testLLMConnection() {
    const btn = document.getElementById("btn-test-llm");
    const statusBox = document.getElementById("llm-status-box");
    btn.disabled = true;
    btn.textContent = "测试中...";
    statusBox.innerHTML = `<span style="color:#f39c12;">⏳ 正在向 DeepSeek 发起握手探测...</span>`;

    try {
        const res = await fetch("/api/llm/test", { method: "POST" });
        const data = await res.json();
        if (data.success) {
            statusBox.innerHTML = `<span style="color:#2ecc71;">✅ ${data.message}</span>`;
        } else {
            statusBox.innerHTML = `<span style="color:#e74c3c;">❌ ${data.message}</span>`;
        }
    } catch (e) {
        statusBox.innerHTML = `<span style="color:#e74c3c;">❌ 网络请求失败: ${e.message}</span>`;
    } finally {
        btn.disabled = false;
        btn.textContent = "⚡ 测试连接";
    }
}

async function saveLLMConfig() {
    const keyInput = document.getElementById("llm-api-key");
    const modelSelect = document.getElementById("llm-model-select");
    const baseInput = document.getElementById("llm-api-base");
    const btn = document.getElementById("btn-save-llm");

    const apiKey = keyInput.value.trim();
    const model = modelSelect.value;
    const apiBase = baseInput.value.trim() || "https://api.deepseek.com";

    if (!apiKey && !llmStatus.is_configured) {
        alert("请输入有效的 DeepSeek API Key (如 sk-...)");
        return;
    }

    btn.disabled = true;
    btn.textContent = "保存中...";

    try {
        const res = await fetch("/api/llm/config", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                api_key: apiKey || (llmStatus.is_configured ? "KEEP_EXISTING" : ""),
                api_base: apiBase,
                model: model
            })
        });
        const data = await res.json();
        if (data.success) {
            llmStatus = data.status;
            updateLLMUI();
            alert("🎉 DeepSeek 大模型配置保存成功！13 位成员即刻拥有即时互动灵魂！");
            keyInput.value = "";
        }
    } catch (e) {
        alert("保存配置失败，请检查网络！");
    } finally {
        btn.disabled = false;
        btn.textContent = "💾 保存并激活";
    }
}

async function clearLLMConfig() {
    if (!confirm("确定要清空 API Key 并切回纯本地精修词库保底模式吗？")) return;

    try {
        const res = await fetch("/api/llm/config", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ api_key: "", api_base: "https://api.deepseek.com", model: "deepseek-chat" })
        });
        const data = await res.json();
        llmStatus = data.status;
        updateLLMUI();
        alert("已清空 API Key，当前已无缝切回本地精修词库模式。");
    } catch (e) {
        console.error(e);
    }
}
