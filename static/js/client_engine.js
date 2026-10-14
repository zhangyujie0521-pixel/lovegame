// -*- coding: utf-8 -*-
/**
 * ASTERIA 纯前端客户端单机状态机与直连 DeepSeek 引擎
 * 支持 GitHub Pages 纯静态托管下的 100% 完整体验：
 * 1. 随机亲哥 + 12抽1暗恋者 + 11人零好感
 * 2. 秘密地下情 (3人上限) 与 4人全员黑化暴雷
 * 3. 浏览器端直连 DeepSeek API (支持 CORS，Key 存储在本地 localStorage)
 * 4. 离线精修台词保底
 */

class ClientGameEngine {
    constructor() {
        this.STORAGE_KEY = "ASTERIA_STATE_V1";
        this.LLM_KEY = "ASTERIA_LLM_CONFIG";
        this.state = null;
        this.loadState();
    }

    loadState() {
        try {
            const raw = localStorage.getItem(this.STORAGE_KEY);
            if (raw) {
                this.state = JSON.parse(raw);
            }
        } catch (e) {
            console.error("读取本地游戏存档失败", e);
        }
    }

    saveState() {
        try {
            localStorage.setItem(this.STORAGE_KEY, JSON.stringify(this.state));
        } catch (e) {
            console.error("保存本地游戏存档失败", e);
        }
    }

    getLLMConfig() {
        try {
            const raw = localStorage.getItem(this.LLM_KEY);
            if (raw) return JSON.parse(raw);
        } catch (e) {}
        return {
            api_key: "",
            api_base: "https://api.deepseek.com",
            model: "deepseek-chat"
        };
    }

    saveLLMConfig(cfg) {
        localStorage.setItem(this.LLM_KEY, JSON.stringify(cfg));
    }

    resetGame(playerName = "林初", careerId = "stylist") {
        const data = window.GAME_DATA;
        if (!data) return null;

        const career = data.careers.find(c => c.id === careerId) || data.careers[0];
        const characters = JSON.parse(JSON.stringify(data.characters));

        // 随机亲哥
        const brotherIdx = Math.floor(Math.random() * characters.length);
        const brother = characters[brotherIdx];

        // 从剩余 12 人随机暗恋者
        const remaining = characters.filter(c => c.id !== brother.id);
        const crush = remaining[Math.floor(Math.random() * remaining.length)];

        // 初始化 13 位成员状态
        const charStatusMap = {};
        characters.forEach(c => {
            const isBrother = (c.id === brother.id);
            const isCrush = (c.id === crush.id);
            let role = "member";
            let affinity = 0;
            if (isBrother) {
                role = "brother";
                affinity = 100;
            } else if (isCrush) {
                role = "secret_crush";
                affinity = 25;
            }

            charStatusMap[c.id] = {
                id: c.id,
                name: c.name,
                role: role,
                affinity: affinity,
                is_dating: false,
                is_blackened: false,
                jealousy: 0,
                age_rank: c.age_rank,
                age_title: c.age_title,
                unit: c.unit,
                unit_role: c.unit_role,
                mbti: c.mbti,
                traits: c.traits,
                avatar_color: c.avatar_color,
                korean_hint: c.korean_hint,
                desc: c.desc,
                quote: isBrother ? c.brother_quote : (isCrush ? c.crush_quote : "练习室见。")
            };
        });

        // 初始大群消息
        const groupMessages = [
            {
                sender_id: "system",
                sender_name: "系统通知",
                text: `欢迎 ${playerName}（${brother.name}的亲妹妹，新任【${career.name}】）加入 ASTERIA 官方群聊！`,
                time: "刚刚"
            },
            {
                sender_id: brother.id,
                sender_name: brother.name,
                text: "大家注意点分寸。我妹妹刚来，谁要是敢欺负她，晚上别想睡觉。",
                time: "刚刚"
            },
            {
                sender_id: crush.id,
                sender_name: crush.name,
                text: "欢迎……好久不见了。",
                time: "刚刚"
            }
        ];

        this.state = {
            is_active: true,
            player_name: playerName,
            career: career,
            brother_id: brother.id,
            brother_name: brother.name,
            crush_id: crush.id,
            crush_name: crush.name,
            characters: charStatusMap,
            dating_list: [],
            is_total_blackened: false,
            story_index: 0,
            group_messages: groupMessages,
            private_chats: {},
            unlocked_cards: [],
            system_logs: [
                `【命运启动】你作为【${career.name}】，踏入顶流男团 ASTERIA 的世界。`,
                `【血缘羁绊】你的亲哥哥是：${brother.age_title} · ${brother.name}！`,
                `【命运注定】在 12 位队友中，有一位少年从练习生时期就默默暗恋着你……`
            ]
        };

        this.saveState();
        return this.getSummary();
    }

    getSummary() {
        if (!this.state || !this.state.is_active) {
            return { is_active: false };
        }

        const datingCount = this.state.dating_list.length;
        const datingNames = this.state.dating_list.map(cid => this.state.characters[cid]?.name).filter(Boolean);
        const sortedMembers = Object.values(this.state.characters).sort((a, b) => a.age_rank - b.age_rank);

        return {
            is_active: true,
            player_name: this.state.player_name,
            career: this.state.career,
            brother_id: this.state.brother_id,
            brother_name: this.state.brother_name,
            crush_id: this.state.crush_id,
            crush_name: this.state.crush_name,
            dating_count: datingCount,
            dating_names: datingNames,
            is_total_blackened: this.state.is_total_blackened,
            blacken_warning: (
                this.state.is_total_blackened ? "🚨 致命警报：全团黑化已引爆！"
                : (datingCount === 3 ? "⚠️ 危险边缘：秘密交往 3/3 人，若达 4 人将彻底引爆全团黑化！"
                : `当前秘密地下情：${datingCount}/3 人（在所有人不知情下隐秘进行）`)
            ),
            members: sortedMembers,
            story_index: this.state.story_index,
            unlocked_cards_count: this.state.unlocked_cards.length,
            system_logs: this.state.system_logs.slice(-8)
        };
    }

    advanceAffinity(charId, delta, reason = "") {
        const char = this.state.characters[charId];
        if (!char || char.role === "brother") return;
        char.affinity = Math.max(0, Math.min(100, char.affinity + delta));
        this.saveState();
    }

    startDating(charId) {
        const char = this.state.characters[charId];
        if (!char) return { success: false, message: "角色不存在" };
        if (char.role === "brother") return { success: false, message: "不能与亲哥哥交往！" };
        if (char.is_dating) return { success: false, message: `已经与 ${char.name} 在秘密交往中！` };

        char.is_dating = true;
        this.state.dating_list.push(charId);

        let isBlackened = false;
        if (this.state.dating_list.length >= 4 && !this.state.is_total_blackened) {
            this.state.is_total_blackened = true;
            Object.values(this.state.characters).forEach(c => {
                c.is_blackened = true;
                c.jealousy = 100;
            });
            isBlackened = true;
        }

        this.saveState();
        return {
            success: true,
            char_name: char.name,
            dating_count: this.state.dating_list.length,
            is_blackened: isBlackened
        };
    }

    drawGacha() {
        const cards = window.GAME_DATA.gachaCards;
        const card = cards[Math.floor(Math.random() * cards.length)];
        this.state.unlocked_cards.push(card);

        // 好感度加成
        if (this.state.characters[card.char_id]) {
            const delta = (card.tier === "SSR" ? 10 : 5);
            this.advanceAffinity(card.char_id, delta);
        }
        this.saveState();
        return card;
    }

    // 纯前端调用 DeepSeek
    async callDeepSeek(messages, temperature = 0.85) {
        const cfg = this.getLLMConfig();
        if (!cfg.api_key || cfg.api_key.length < 5) return null;

        const url = `${cfg.api_base.replace(/\/+$/, "")}/chat/completions`;
        try {
            const res = await fetch(url, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${cfg.api_key}`
                },
                body: JSON.stringify({
                    model: cfg.model || "deepseek-chat",
                    messages: messages,
                    temperature: temperature,
                    max_tokens: 300
                })
            });

            if (res.ok) {
                const data = await res.json();
                return data.choices[0].message.content.trim();
            } else {
                console.warn("DeepSeek 响应异常:", res.status);
            }
        } catch (e) {
            console.error("DeepSeek 直连请求失败:", e);
        }
        return null;
    }

    // 前端直接生成 1v1 私聊回复
    async handlePrivateMessage(charId, text) {
        const char = this.state.characters[charId];
        if (!this.state.private_chats[charId]) {
            this.state.private_chats[charId] = [];
        }

        // 添加用户消息
        this.state.private_chats[charId].push({ sender: "player", text: text, time: "刚刚" });

        let replyText = null;
        let source = "fallback";

        // 尝试调用 DeepSeek
        const cfg = this.getLLMConfig();
        if (cfg.api_key) {
            const systemPrompt = `你正在扮演 13 人自制作偶像男团 ASTERIA 的成员 ${char.name}（#${char.age_rank} ${char.age_title}，${char.unit}，性格特质：${char.traits.join(",")}）。
女主名为 ${this.state.player_name}，职业是【${this.state.career.name}】。
你与她的关系：${char.role === 'brother' ? '【亲哥哥(绝对护妹防狼门禁严苛)】' : (char.is_dating ? '【秘密地下男友(隐秘甜蜜偷恋)】' : (char.role === 'secret_crush' ? '【练习生旧识暗恋者(酸涩深情)】' : '【普通队友】'))}。
${this.state.is_total_blackened ? '【🚨全团4人黑化暴雷状态！你陷入了极端占有欲、病娇疯魔、门锁了休想离开】' : ''}
请用中文以乙女游戏角色的口吻回复她（带动作神态描写，如“（微微侧头）”，字数在30~80字，避免崩人设）。`;

            const historyMsgs = this.state.private_chats[charId].slice(-5).map(m => ({
                role: m.sender === "player" ? "user" : "assistant",
                content: m.text
            }));

            const raw = await this.callDeepSeek([{ role: "system", content: systemPrompt }, ...historyMsgs]);
            if (raw) {
                replyText = raw;
                source = "deepseek";
                this.advanceAffinity(charId, 2);
            }
        }

        // 降级保底
        if (!replyText) {
            if (this.state.is_total_blackened) {
                replyText = char.quote || "（冷冷地看着你，门外传来了落锁的声音）";
            } else if (char.role === "brother") {
                replyText = `【亲哥专属叮嘱】${char.quote}`;
            } else if (char.is_dating) {
                replyText = `【秘密恋人】想我了？排练完后门见，千万别让你哥发现了。`;
                this.advanceAffinity(charId, 2);
            } else if (char.role === "secret_crush") {
                replyText = `看到你发来消息，我手心都在出汗……今晚有空吗？我有话想单独对你说。`;
                this.advanceAffinity(charId, 3);
            } else {
                replyText = `是妹妹啊。听你哥提起过你很多次，今天工作辛苦了！`;
                this.advanceAffinity(charId, 2);
            }
        }

        this.state.private_chats[charId].push({ sender: "char", text: replyText, time: "刚刚" });
        this.saveState();

        return {
            reply: replyText,
            history: this.state.private_chats[charId],
            character: this.state.characters[charId],
            source: source
        };
    }

    // 前端直接生成 13 人大群回复
    async handleGroupMessage(text) {
        this.state.group_messages.push({
            sender_id: "player",
            sender_name: this.state.player_name,
            text: text,
            time: "刚刚"
        });

        const brother = this.state.characters[this.state.brother_id];
        const crush = this.state.characters[this.state.crush_id];
        const datingList = this.state.dating_list;

        const replies = [];
        if (this.state.is_total_blackened) {
            replies.push({
                sender_id: brother.id,
                sender_name: brother.name,
                text: `@${this.state.player_name} 把门开开，我们都在门外。`,
                time: "刚刚"
            });
            if (datingList.length > 0) {
                const b = this.state.characters[datingList[0]];
                replies.push({
                    sender_id: b.id,
                    sender_name: b.name,
                    text: "别白费力气了。今天谁在群里也救不了你。",
                    time: "刚刚"
                });
            }
        } else {
            // 亲哥防狼
            const broReplies = [
                `@${this.state.player_name} 晚上别聊太晚，十点准时回房间睡觉。`,
                `大晚上的发什么消息？你们几个臭小子别在群里起哄。`,
                `妹妹饿不饿？哥给你去买夜宵，不准理那些想约你出去的人。`
            ];
            replies.push({
                sender_id: brother.id,
                sender_name: brother.name,
                text: broReplies[Math.floor(Math.random() * broReplies.length)],
                time: "刚刚"
            });

            if (datingList.length > 0) {
                const bId = datingList[Math.floor(Math.random() * datingList.length)];
                const b = this.state.characters[bId];
                replies.push({
                    sender_id: b.id,
                    sender_name: b.name,
                    text: `（私下发了一个小猫探头表情，群里装正经）收到，大家都早点休息吧。`,
                    time: "刚刚"
                });
            } else {
                replies.push({
                    sender_id: crush.id,
                    sender_name: crush.name,
                    text: `今天辛苦了，明天排练我会好好表现的。`,
                    time: "刚刚"
                });
            }
        }

        replies.forEach(r => this.state.group_messages.push(r));
        this.saveState();
        return this.state.group_messages;
    }
}

window.clientEngine = new ClientGameEngine();
