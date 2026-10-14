# -*- coding: utf-8 -*-
"""
ASTERIA 顶流男团乙女恋爱游戏 - DeepSeek 大模型驱动模块
支持：
1. 1v1 私聊拟真推拉（人设深度还原、兄妹防狼、地下情暗号、暗恋隐忍、黑化病娇）
2. 13 人官方大群动态抢答与修罗场联动
3. 优雅双轨制：若未配置 API Key 或请求超时，无缝回退到本地高品质词库
"""

import os
import json
import logging
import httpx
from typing import Dict, List, Any, Optional

logger = logging.getLogger("asteria_llm")
logging.basicConfig(level=logging.INFO)

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "llm_config.json")

class LLMService:
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY", "")
        self.api_base = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com").rstrip("/")
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self.load_config()

    def load_config(self):
        """从本地文件加载持久化配置"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("api_key"):
                        self.api_key = data["api_key"]
                    if data.get("api_base"):
                        self.api_base = data["api_base"].rstrip("/")
                    if data.get("model"):
                        self.model = data["model"]
            except Exception as e:
                logger.error(f"加载 LLM 配置失败: {e}")

    def save_config(self, api_key: str, api_base: Optional[str] = None, model: Optional[str] = None):
        """保存配置"""
        if api_key != "KEEP_EXISTING":
            self.api_key = api_key.strip()
        if api_base:
            self.api_base = api_base.strip().rstrip("/")
        if model:
            self.model = model.strip()

        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "api_key": self.api_key,
                    "api_base": self.api_base,
                    "model": self.model
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"持久化 LLM 配置失败: {e}")

    def is_configured(self) -> bool:
        return bool(self.api_key and len(self.api_key) > 5)

    def get_status(self) -> Dict[str, Any]:
        return {
            "is_configured": self.is_configured(),
            "model": self.model,
            "api_base": self.api_base,
            "masked_key": f"{self.api_key[:4]}****{self.api_key[-4:]}" if self.is_configured() else ""
        }

    async def test_connection(self) -> Dict[str, Any]:
        """测试 DeepSeek 连接状态"""
        if not self.is_configured():
            return {"success": False, "message": "尚未配置 DeepSeek API Key"}

        url = f"{self.api_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": "你好，请用一句话确认连接正常。"}
            ],
            "max_tokens": 30
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    reply = res.json()["choices"][0]["message"]["content"]
                    return {"success": True, "message": f"连接成功！模型回应: {reply}"}
                else:
                    return {"success": False, "message": f"接口返回错误: HTTP {res.status_code} - {res.text}"}
        except Exception as e:
            return {"success": False, "message": f"连接异常: {str(e)}"}

    def _build_character_prompt(self, char: Dict[str, Any], game_state: Dict[str, Any]) -> str:
        """构建 1v1 私聊男主专属拟真人设 Prompt"""
        player_name = game_state.get("player_name", "林初")
        career_name = game_state.get("career", {}).get("name", "化妆造型师")
        brother_name = game_state.get("brother_name", "顾寒沉")
        dating_list = game_state.get("dating_list", [])
        is_total_blackened = game_state.get("is_total_blackened", False)
        
        char_id = char["id"]
        role = char.get("role", "member")
        is_dating = char_id in dating_list
        is_brother = (role == "brother")
        is_crush = (role == "secret_crush")
        affinity = char.get("affinity", 0)

        # 关系描述与心态
        if is_total_blackened or char.get("is_blackened"):
            relationship_desc = (
                "【全团暴雷黑化状态】！整个 ASTERIA 发现女主同时脚踏多条船，彻底理智断线。"
                "你处于极度占有欲、病娇、阴鸷、疯批的修罗场状态。无论你平时多温柔或克制，"
                "此刻你已经锁上门，带着冰冷又危险的压迫感，绝不许她再逃脱。"
            )
        elif is_brother:
            relationship_desc = (
                f"【血浓于水的亲哥哥（绝对不可攻略，亲情锁死）】！"
                f"你是 13 人男团里最具家长威严的护妹狂魔。全团另外 12 个臭小子谁敢接近你妹妹，你都极度警觉防狼。"
                f"对妹妹说话表面严肃查岗（抓门禁、盯晚饭、查交友），骨子里无底线宠溺护短。"
            )
        elif is_dating:
            other_datings = [c["name"] for cid, c in game_state.get("characters", {}).items() if cid in dating_list and cid != char_id]
            relationship_desc = (
                f"【秘密地下恋人】！你和女主瞒着全团所有人和她亲哥 {brother_name}，正在进行绝对不能被发现的地下恋情。"
                f"说话充满秘密情侣之间的暧昧、专属昵称、只有彼此懂的暗号，渴望独处但又小心翼翼怕被队友撞破。"
            )
        elif is_crush:
            relationship_desc = (
                f"【隐藏暗恋者】！你从籍籍无名的地下室练习生时期起，就暗恋着身为队友亲妹妹的女主。"
                f"由于队友（她哥）在场，你一直隐忍克制。你的每一句回复都暗藏酸涩、小心翼翼与渴望靠近的试探。"
            )
        else:
            relationship_desc = (
                f"【普通队友（当前好感度：{affinity}/100）】。她是队友 {brother_name} 的亲妹妹，新来的【{career_name}】。"
                f"你尊重队友的妹妹，目前处于正常的熟人破冰或微微心动阶段，随着好感提升会越来越在意她。"
            )

        prompt = f"""你正在扮演乙女恋爱模拟游戏中的男主角。请完全沉浸在该角色中，用符合他性格、语调与心理活动的口吻与女主角直接对话。

【世界观设定】
- 偶像男团：ASTERIA（13人大型自制作顶流男团，灵感源自 SEVENTEEN）
- 女主角：{player_name}，亲哥在团里，现在的职业是：【{career_name}】
- 你的身份档案：
  * 姓名：{char['name']}（顺位：#{char['age_rank']} · {char['age_title']}）
  * 分队与职位：{char['unit']} · {char.get('unit_role', '核心成员')}
  * MBTI与特质：{char['mbti']} · {', '.join(char.get('traits', []))}
  * 性格深度画像：{char['desc']}
  * 标志性口吻/专属台词参考：{char.get('quote', '')}

【你与女主的当前关系】
{relationship_desc}

【对话要求】
1. 语言：中文。保持乙女游戏轻小说/短剧质感，回复精炼生动，字数在 30~80 字左右（1~3句话）。
2. 可自然融入微动作或神态描写（用括号表示，例如“（微微侧头，耳尖泛红）”或“（垂下眼睫低笑一声）”）。
3. 严格遵循你的人设、当前的暗恋/地下情/兄妹/黑化状态，严禁出现崩人设、说教或像 AI 助手的发言。
4. 在回答末尾，另起一行输出一个 JSON 标签用于游戏引擎结算好感变动（格式：[AFFINITY_DELTA: 整数]，如 [AFFINITY_DELTA: 2]，范围一般在 1 到 3，黑化状态下可为 0 或输出 [JEALOUSY_DELTA: 5]）。用户前端界面不会展示此标签。
"""
        return prompt

    async def generate_private_reply(self, char: Dict[str, Any], game_state: Dict[str, Any], user_text: str, history: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """调用 DeepSeek 生成 1v1 私聊回复"""
        if not self.is_configured():
            return None

        system_prompt = self._build_character_prompt(char, game_state)
        messages = [{"role": "system", "content": system_prompt}]

        # 添加最近 4 条历史
        recent_history = history[-4:] if len(history) > 4 else history
        for msg in recent_history:
            role = "user" if msg.get("sender") == "player" else "assistant"
            # 清除可能残留的标签
            clean_text = msg.get("text", "").split("[AFFINITY_DELTA:")[0].strip()
            messages.append({"role": role, "content": clean_text})

        messages.append({"role": "user", "content": user_text})

        url = f"{self.api_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.85,
            "max_tokens": 200
        }

        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                res = await client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    raw_content = res.json()["choices"][0]["message"]["content"].strip()
                    # 解析好感度标签
                    affinity_delta = 2
                    import re
                    match = re.search(r"\[AFFINITY_DELTA:\s*(-?\d+)\]", raw_content)
                    if match:
                        affinity_delta = int(match.group(1))
                        raw_content = re.sub(r"\[AFFINITY_DELTA:\s*-?\d+\]", "", raw_content).strip()

                    match_j = re.search(r"\[JEALOUSY_DELTA:\s*(-?\d+)\]", raw_content)
                    if match_j:
                        raw_content = re.sub(r"\[JEALOUSY_DELTA:\s*-?\d+\]", "", raw_content).strip()

                    return {
                        "reply": raw_content,
                        "affinity_delta": affinity_delta
                    }
                else:
                    logger.warning(f"DeepSeek API 报错: {res.status_code} - {res.text}")
                    return None
        except Exception as e:
            logger.error(f"DeepSeek 请求异常: {e}")
            return None

    def _build_group_prompt(self, game_state: Dict[str, Any]) -> str:
        """构建 13 人大群修罗场 Prompt"""
        player_name = game_state.get("player_name", "林初")
        career_name = game_state.get("career", {}).get("name", "化妆造型师")
        brother_id = game_state.get("brother_id")
        brother_name = game_state.get("brother_name", "顾寒沉")
        crush_id = game_state.get("crush_id")
        crush_name = game_state.get("crush_name", "")
        dating_list = game_state.get("dating_list", [])
        is_total_blackened = game_state.get("is_total_blackened", False)

        members_info = []
        for cid, c in game_state.get("characters", {}).items():
            tag = []
            if cid == brother_id:
                tag.append("亲哥哥(严防死守)")
            elif cid in dating_list:
                tag.append("秘密地下男友(隐蔽暧昧)")
            elif cid == crush_id:
                tag.append("暗恋者(隐忍酸涩)")
            else:
                tag.append("普通队员")
            members_info.append(f"- ID: {cid}, 姓名: {c['name']}, 角色: {c['age_title']}, 性格: {','.join(c.get('traits', []))}, 关系: {','.join(tag)}")

        members_str = "\n".join(members_info)

        return f"""你正在模拟 13 人自制作偶像男团 ASTERIA 的官方微信大群。
女主名为 {player_name}，职业是【{career_name}】。
全团 13 位成员档案及与女主关系如下：
{members_str}

【当前全团状态】：{'🚨 全团4人黑化暴雷状态！全员阴鸷病娇修罗场！' if is_total_blackened else '正常营业与排练日常，暗流涌动'}

【任务指令】：
女主在群里发了一条消息。请你选择 2 到 3 位成员在群内进行真实的抢答或斗嘴！
必须包括：
1. 亲哥哥（{brother_name}）：永远第一时间出现查岗、提醒门禁、警惕队里臭小子打主意；
2. 另外 1~2 位相关成员：秘密地下男友（若有，暗中护短或递暗号）、暗恋者（酸涩回应）、或团霸忙内/活宝成员（如言夏、黎诺、裴燃活跃起哄）。

【严格输出格式】：
输出严格的 JSON 数组，每条包含 sender_id, sender_name, text：
[
  {{"sender_id": "成员ID", "sender_name": "成员名字", "text": "发言内容"}},
  ...
]
发言内容保持鲜活日常、男团大群感，每条 15~35 字左右，严禁输出任何额外多余文本。"""

    async def generate_group_reply(self, game_state: Dict[str, Any], user_text: str) -> Optional[List[Dict[str, Any]]]:
        """大群消息 DeepSeek 联动生成"""
        if not self.is_configured():
            return None

        system_prompt = self._build_group_prompt(game_state)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"女主【{game_state.get('player_name', '林初')}】在群里说：{user_text}"}
        ]

        url = f"{self.api_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.85,
            "response_format": {"type": "json_object"} if "deepseek" in self.model else None,
            "max_tokens": 300
        }

        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                res = await client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    content = res.json()["choices"][0]["message"]["content"].strip()
                    # 尝试解析为 JSON
                    try:
                        parsed = json.loads(content)
                        # 如果是 dict 带 messages 键或列表
                        if isinstance(parsed, list):
                            return parsed
                        elif isinstance(parsed, dict):
                            for k in ["replies", "messages", "data"]:
                                if k in parsed and isinstance(parsed[k], list):
                                    return parsed[k]
                            # 如果 dict 直接是单条，包装为 list
                            if "sender_id" in parsed:
                                return [parsed]
                    except Exception:
                        pass
                else:
                    logger.warning(f"大群 DeepSeek 报错: {res.status_code}")
                    return None
        except Exception as e:
            logger.error(f"大群 DeepSeek 请求异常: {e}")
            return None

# 全局单例
llm = LLMService()
