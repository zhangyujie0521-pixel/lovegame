# -*- coding: utf-8 -*-
"""
游戏全局状态机 (Game State Manager)
包含：开局双重抽签（1哥哥+1暗恋+11零好感）、好感度计算、秘密交往（最多3人）、全团黑化（4人暴雷）、上位判定等
"""

import random
import copy
from typing import Dict, List, Any, Optional
from data.characters import CHARACTERS_DATA, CAREERS_DATA
from data.gacha_cards import GACHA_CARDS
from data.stories import STORY_CHAPTERS, USURPER_EVENT, TOTAL_COLLAPSE_EVENT


class GameManager:
    def __init__(self):
        self.state: Dict[str, Any] = {}
        self.reset_game()

    def reset_game(self, player_name: str = "林初", career_id: str = "stylist") -> Dict[str, Any]:
        """初始化全新游戏 (从0开始，非二周目，重新随机抽取哥哥与暗恋者)"""
        # 1. 查找职业
        career = next((c for c in CAREERS_DATA if c["id"] == career_id), CAREERS_DATA[0])

        # 2. 复制 13 个人物列表
        characters = copy.deepcopy(CHARACTERS_DATA)

        # 3. 随机抽取 1 人为亲哥哥
        brother = random.choice(characters)
        brother_id = brother["id"]

        # 4. 从剩余 12 人中抽取 1 人为秘密暗恋者
        remaining_12 = [c for c in characters if c["id"] != brother_id]
        secret_crush = random.choice(remaining_12)
        crush_id = secret_crush["id"]

        # 5. 初始化每位成员的好感度与状态
        char_status_map = {}
        for c in characters:
            cid = c["id"]
            if cid == brother_id:
                role = "brother"
                affinity = 100  # 亲情锁定
                dating = False
            elif cid == crush_id:
                role = "secret_crush"
                affinity = 25   # 练习生时期的暗恋微好感
                dating = False
            else:
                role = "member"
                affinity = 0    # 其余11人纯路人队友 0 好感
                dating = False

            char_status_map[cid] = {
                "id": cid,
                "name": c["name"],
                "role": role,  # 'brother', 'secret_crush', 'member'
                "affinity": affinity,
                "is_dating": dating,
                "is_blackened": False,
                "jealousy": 0,
                "age_rank": c["age_rank"],
                "age_title": c["age_title"],
                "unit": c["unit"],
                "mbti": c["mbti"],
                "traits": c["traits"],
                "avatar_color": c["avatar_color"],
                "korean_hint": c["korean_hint"],
                "desc": c["desc"],
                "brother_style": c["brother_style"] if role == "brother" else "",
                "quote": c["brother_quote"] if role == "brother" else (c["crush_quote"] if role == "secret_crush" else "练习室见。")
            }

        # 6. 初始化 13 人大群初始消息
        group_messages = [
            {
                "sender_id": "system",
                "sender_name": "系统通知",
                "text": f"欢迎 {player_name}（{brother['name']}的亲妹妹，新任【{career['name']}】）加入 ASTERIA 官方群聊！",
                "time": "刚刚"
            },
            {
                "sender_id": brother_id,
                "sender_name": brother["name"],
                "text": "大家注意点分寸。我妹妹刚来，谁要是敢欺负她，晚上别想睡觉。",
                "time": "刚刚"
            },
            {
                "sender_id": crush_id,
                "sender_name": secret_crush["name"],
                "text": "欢迎……好久不见了。",
                "time": "刚刚"
            }
        ]

        # 7. 全局状态组装
        self.state = {
            "is_active": True,
            "player_name": player_name,
            "career": career,
            "brother_id": brother_id,
            "brother_name": brother["name"],
            "crush_id": crush_id,
            "crush_name": secret_crush["name"],
            "characters": char_status_map,
            "dating_list": [],          # 当前秘密交往名单 (id 列表，上限 3)
            "is_total_blackened": False, # 是否触发全团 4 人暴雷黑化
            "story_index": 0,            # 主线进度
            "group_messages": group_messages,
            "private_chats": {c["id"]: [] for c in characters},
            "unlocked_cards": [],        # 抽到的卡牌
            "system_logs": [
                f"【命运启动】你作为【{career['name']}】，踏入顶流男团 ASTERIA 的世界。",
                f"【血缘羁绊】你的亲哥哥是：{brother['age_title']} · {brother['name']}！",
                f"【命运注定】在 12 位队友中，有一位少年从练习生时期就默默暗恋着你……"
            ]
        }
        return self.get_summary()

    def get_summary(self) -> Dict[str, Any]:
        """获取当前全局仪表盘与状态信息"""
        if not self.state.get("is_active"):
            return {"is_active": False}

        dating_count = len(self.state["dating_list"])
        dating_names = [self.state["characters"][cid]["name"] for cid in self.state["dating_list"]]

        # 排序：严格按照 age_rank 排序 13 个人
        sorted_members = sorted(
            list(self.state["characters"].values()),
            key=lambda x: x["age_rank"]
        )

        return {
            "is_active": True,
            "player_name": self.state["player_name"],
            "career": self.state["career"],
            "brother_id": self.state["brother_id"],
            "brother_name": self.state["brother_name"],
            "crush_id": self.state["crush_id"],
            "crush_name": self.state["crush_name"],
            "dating_count": dating_count,
            "dating_names": dating_names,
            "is_total_blackened": self.state["is_total_blackened"],
            "blacken_warning": (
                "🚨 致命警报：全团黑化已引爆！" if self.state["is_total_blackened"]
                else (f"⚠️ 危险边缘：秘密交往 {dating_count}/3 人，若达 4 人将彻底引爆全团黑化！" if dating_count == 3
                      else f"当前秘密地下情：{dating_count}/3 人（在所有人不知情下隐秘进行）")
            ),
            "members": sorted_members,
            "story_index": self.state["story_index"],
            "unlocked_cards_count": len(self.state["unlocked_cards"]),
            "system_logs": self.state["system_logs"][-8:]
        }

    def check_blackening(self):
        """检查是否满足 4 人黑化暴雷条件"""
        if len(self.state["dating_list"]) >= 4 and not self.state["is_total_blackened"]:
            self.state["is_total_blackened"] = True
            for cid in self.state["characters"]:
                self.state["characters"][cid]["is_blackened"] = True
                self.state["characters"][cid]["jealousy"] = 100
            self.state["system_logs"].append("💥【全团黑化暴雷】你同时脚踏 4 条船的秘密在宿舍彻底曝光！ASTERIA 全员理智断线！")
            return True
        return False

    def advance_affinity(self, char_id: str, delta: int, reason: str = ""):
        """提升或降低好感度"""
        if char_id not in self.state["characters"]:
            return
        char = self.state["characters"][char_id]
        if char["role"] == "brother":
            # 亲情满值，只增加亲情互动
            return

        old_aff = char["affinity"]
        char["affinity"] = max(0, min(100, old_aff + delta))
        self.state["system_logs"].append(f"【好感变动】{char['name']} 好感度 {'+' if delta >= 0 else ''}{delta} (当前: {char['affinity']}) {reason}")

        # 如果好感度达到 60 且未交往且尚未全团黑化，可自动触发告白或交往
        if char["affinity"] >= 60 and not char["is_dating"] and len(self.state["dating_list"]) < 4:
            # 检查是否交往
            pass

    def start_dating(self, char_id: str) -> Dict[str, Any]:
        """开启与某个角色的秘密交往"""
        if char_id not in self.state["characters"]:
            return {"success": False, "message": "角色不存在"}
        char = self.state["characters"][char_id]
        if char["role"] == "brother":
            return {"success": False, "message": "不能与亲哥哥交往！"}
        if char["is_dating"]:
            return {"success": False, "message": f"已经与 {char['name']} 在秘密交往中！"}

        char["is_dating"] = True
        self.state["dating_list"].append(char_id)
        self.state["system_logs"].append(f"💖【地下秘恋】你与 {char['name']} 确立了秘密恋爱关系！（当前共计秘密交往 {len(self.state['dating_list'])} 人）")

        # 检查是否触发第 4 人全团黑化
        is_blackened = self.check_blackening()

        return {
            "success": True,
            "char_name": char["name"],
            "dating_count": len(self.state["dating_list"]),
            "is_blackened": is_blackened
        }

    def trigger_usurper(self, action: str) -> Dict[str, Any]:
        """处理暗恋者上位事件抉择"""
        crush_id = self.state["crush_id"]
        crush = self.state["characters"][crush_id]

        if action == "accept_usurper":
            # 暗恋者上位，成为秘密交往对象
            if crush_id not in self.state["dating_list"]:
                self.state["dating_list"].append(crush_id)
                crush["is_dating"] = True
            crush["affinity"] = min(100, crush["affinity"] + 30)
            self.state["system_logs"].append(f"🔥【暗恋者上位】{crush['name']} 成功上位！在暴雨夜与你确立了秘密关系！")
            is_blackened = self.check_blackening()
            return {"success": True, "action": action, "is_blackened": is_blackened, "msg": f"{crush['name']} 强势上位！"}
        elif action == "double_dating":
            # 隐瞒双开
            if crush_id not in self.state["dating_list"]:
                self.state["dating_list"].append(crush_id)
                crush["is_dating"] = True
            crush["affinity"] = min(100, crush["affinity"] + 20)
            self.state["system_logs"].append(f"🤫【秘密双开】你将 {crush['name']} 发展为另一位地下情人！")
            is_blackened = self.check_blackening()
            return {"success": True, "action": action, "is_blackened": is_blackened, "msg": "心跳双开成功！"}
        else:
            crush["affinity"] = max(0, crush["affinity"] - 10)
            self.state["system_logs"].append(f"💔【上位失败】你狠心拒绝了 {crush['name']} 的暴雨夜告白。")
            return {"success": True, "action": action, "is_blackened": False, "msg": "已拒绝暗恋者上位。"}

    def draw_gacha(self) -> Dict[str, Any]:
        """单抽抽卡"""
        card = copy.deepcopy(random.choice(GACHA_CARDS))
        # 增加好感度
        cid = card["char_id"]
        if cid in self.state["characters"] and self.state["characters"][cid]["role"] != "brother":
            self.advance_affinity(cid, 8, f"(抽取专属卡面【{card['title']}】)")

        self.state["unlocked_cards"].append(card)
        self.state["system_logs"].append(f"✨【心动抽卡】抽取到 {card['tier']} 珍稀卡面：【{card['char_name']} · {card['title']}】！")
        return card


game = GameManager()
