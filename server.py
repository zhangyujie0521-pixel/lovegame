# -*- coding: utf-8 -*-
"""
ASTERIA 乙女向偶像恋爱模拟游戏 - FastAPI 主服务
"""

import os
import random
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from game_state import game
from data.characters import CHARACTERS_DATA, CAREERS_DATA
from data.gacha_cards import GACHA_CARDS
from data.stories import STORY_CHAPTERS, USURPER_EVENT, TOTAL_COLLAPSE_EVENT
from llm_service import llm

app = FastAPI(title="ASTERIA Idol Otome Game Engine", version="1.0.0")

# 挂载静态资源
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(STATIC_DIR, exist_ok=True)


class NewGameRequest(BaseModel):
    player_name: str = "林初"
    career_id: str = "stylist"


class LLMConfigRequest(BaseModel):
    api_key: str
    api_base: Optional[str] = "https://api.deepseek.com"
    model: Optional[str] = "deepseek-chat"


class GroupMsgRequest(BaseModel):
    text: str


class PrivateMsgRequest(BaseModel):
    char_id: str
    text: str


class StoryChoiceRequest(BaseModel):
    chapter_id: str
    choice_index: int


class UsurperRequest(BaseModel):
    action: str  # 'accept_usurper', 'double_dating', 'reject_usurper'


class DatingRequest(BaseModel):
    char_id: str


@app.get("/api/state")
def get_state():
    """获取全局游戏状态"""
    return game.get_summary()


@app.get("/api/meta")
def get_meta():
    """获取所有职业及元数据"""
    return {
        "careers": CAREERS_DATA,
        "total_characters": len(CHARACTERS_DATA)
    }


@app.get("/api/llm/status")
def get_llm_status():
    """获取当前大模型接入与配置状态"""
    return llm.get_status()


@app.post("/api/llm/config")
def set_llm_config(req: LLMConfigRequest):
    """保存或更新大模型配置"""
    llm.save_config(api_key=req.api_key, api_base=req.api_base, model=req.model)
    return {"success": True, "status": llm.get_status()}


@app.post("/api/llm/test")
async def test_llm_connection():
    """测试当前大模型连接是否通畅"""
    res = await llm.test_connection()
    return res


@app.post("/api/new_game")
def start_new_game(req: NewGameRequest):
    """从 0 开始全新开局（非二周目，随机抽取亲哥与暗恋者）"""
    summary = game.reset_game(player_name=req.player_name, career_id=req.career_id)
    return {"success": True, "state": summary}


@app.get("/api/chat/group")
def get_group_chat():
    """获取 13 人大群消息"""
    return {
        "group_name": f"ASTERIA 官方大群 (14) · 禁止对妹妹心怀不轨",
        "messages": game.state.get("group_messages", [])
    }


@app.post("/api/chat/group/send")
async def send_group_msg(req: GroupMsgRequest):
    """向 13 人大群发送消息，触发成员动态反应 (优先 DeepSeek 大模型驱动，带降级保底)"""
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="消息内容不能为空")

    user_msg = {
        "sender_id": "player",
        "sender_name": game.state["player_name"],
        "text": req.text,
        "time": "刚刚"
    }
    game.state["group_messages"].append(user_msg)

    brother_id = game.state["brother_id"]
    crush_id = game.state["crush_id"]
    dating_list = game.state["dating_list"]
    is_blackened = game.state["is_total_blackened"]

    # 1. 尝试大模型动态生成群聊互动
    llm_replies = None
    if llm.is_configured():
        try:
            llm_replies = await llm.generate_group_reply(game.state, req.text)
        except Exception:
            llm_replies = None

    if llm_replies and isinstance(llm_replies, list) and len(llm_replies) > 0:
        for r in llm_replies:
            r["time"] = "刚刚"
            game.state["group_messages"].append(r)
        return {"success": True, "messages": game.state["group_messages"], "source": "deepseek"}

    # 2. 降级保底逻辑：本地经典回复
    replies = []
    if is_blackened:
        # 黑化状态下的集体窒息发言
        replies.append({
            "sender_id": brother_id,
            "sender_name": game.state["brother_name"],
            "text": f"@{game.state['player_name']} 你还敢在大群说话？把门开开，我们都在门外。",
            "time": "刚刚"
        })
        if dating_list:
            d_id = dating_list[0]
            replies.append({
                "sender_id": d_id,
                "sender_name": game.state["characters"][d_id]["name"],
                "text": "别白费力气了。今天谁发消息也救不了你。",
                "time": "刚刚"
            })
    else:
        # 哥哥护妹防狼
        brother_replies = [
            f"@{game.state['player_name']} 晚上别聊太晚，十点准时回房间睡觉。",
            f"大晚上的发什么消息？你们几个臭小子别在群里起哄。",
            f"妹妹饿不饿？想吃夜宵哥去给你买，不准理那些想约你出去的人。"
        ]
        replies.append({
            "sender_id": brother_id,
            "sender_name": game.state["brother_name"],
            "text": random.choice(brother_replies),
            "time": "刚刚"
        })

        # 如果有秘密男友，或者暗恋者回复
        if dating_list:
            boyfriend_id = random.choice(dating_list)
            boyfriend = game.state["characters"][boyfriend_id]
            replies.append({
                "sender_id": boyfriend_id,
                "sender_name": boyfriend["name"],
                "text": "（私聊发了一个小猫探头表情，但群里装淡定）收到，大家早点休息吧。",
                "time": "刚刚"
            })
        else:
            crush = game.state["characters"][crush_id]
            replies.append({
                "sender_id": crush_id,
                "sender_name": crush["name"],
                "text": f"今天辛苦了，早点休息。明天舞台我会好好表现的。",
                "time": "刚刚"
            })

    game.state["group_messages"].extend(replies)
    return {"success": True, "messages": game.state["group_messages"], "source": "fallback"}


@app.get("/api/chat/private/{char_id}")
def get_private_chat(char_id: str):
    """获取与某位成员的 1v1 私聊历史"""
    if char_id not in game.state["characters"]:
        raise HTTPException(status_code=404, detail="角色不存在")
    char = game.state["characters"][char_id]
    history = game.state["private_chats"].get(char_id, [])
    return {
        "character": char,
        "history": history
    }


@app.post("/api/chat/private/send")
async def send_private_msg(req: PrivateMsgRequest):
    """发送 1v1 私聊消息并获取男主专属互动 (优先 DeepSeek 深度拟真，支持保底)"""
    cid = req.char_id
    if cid not in game.state["characters"]:
        raise HTTPException(status_code=404, detail="角色不存在")

    char = game.state["characters"][cid]
    if cid not in game.state["private_chats"]:
        game.state["private_chats"][cid] = []

    user_msg = {"sender": "player", "text": req.text, "time": "刚刚"}
    game.state["private_chats"][cid].append(user_msg)

    reply_text = None
    source = "fallback"

    # 1. 尝试 DeepSeek 大模型拟真生成
    if llm.is_configured():
        try:
            llm_result = await llm.generate_private_reply(
                char=char,
                game_state=game.state,
                user_text=req.text,
                history=game.state["private_chats"][cid]
            )
            if llm_result and llm_result.get("reply"):
                reply_text = llm_result["reply"]
                delta = llm_result.get("affinity_delta", 2)
                game.advance_affinity(cid, delta, f"（DeepSeek 即时推拉 +{delta}）")
                source = "deepseek"
        except Exception as e:
            reply_text = None

    # 2. 降级保底回复
    if not reply_text:
        is_blackened = game.state["is_total_blackened"]
        if is_blackened:
            reply_text = char["quote"] if char.get("quote") else "（冷冷地看着你，没有回复，但门口传来了转动门把手的声音）"
        elif char["role"] == "brother":
            reply_text = f"【亲哥专属叮嘱】{char['quote']}"
        elif char["is_dating"]:
            reply_text = f"【秘密恋人】想我了？今晚排练完，老地方见。别让你哥察觉到了。"
            game.advance_affinity(cid, 2, "（甜蜜私聊）")
        elif char["role"] == "secret_crush":
            reply_text = f"看到你发消息过来……其实我手心都在出汗。明天有空吗？我有些话，想单独跟你说。"
            game.advance_affinity(cid, 3, "（暗恋心动私戳）")
        else:
            # 普通队友破冰
            reply_text = f"是妹妹啊。听你哥提起你很多次了，今天工作辛苦了！"
            game.advance_affinity(cid, 2, "（日常交流破冰）")

    bot_msg = {"sender": "char", "text": reply_text, "time": "刚刚"}
    game.state["private_chats"][cid].append(bot_msg)

    return {
        "success": True,
        "reply": reply_text,
        "history": game.state["private_chats"][cid],
        "character": game.state["characters"][cid],
        "source": source
    }


@app.get("/api/story/current")
def get_current_story():
    """获取当前主线剧情章节与上位/黑化状态"""
    idx = game.state.get("story_index", 0)
    if idx >= len(STORY_CHAPTERS):
        chapter = STORY_CHAPTERS[-1]
    else:
        chapter = STORY_CHAPTERS[idx]

    # 替换剧本中的占位符
    brother_name = game.state["brother_name"]
    crush_name = game.state["crush_name"]
    career_name = game.state["career"]["name"]

    processed_dialogues = []
    for d in chapter["dialogues"]:
        spk = d["speaker"]
        spk = spk.replace("【亲哥哥】", f"【哥哥 · {brother_name}】")
        spk = spk.replace("【暗恋者】", f"【暗恋者 · {crush_name}】")
        txt = d["text"].replace("【职业身份】", career_name)
        processed_dialogues.append({"speaker": spk, "text": txt})

    # 检查是否满足上位剧情条件
    has_dating = len(game.state["dating_list"]) > 0
    crush_aff = game.state["characters"][game.state["crush_id"]]["affinity"]
    can_trigger_usurper = (has_dating and crush_aff >= 30 and not game.state["characters"][game.state["crush_id"]]["is_dating"])

    return {
        "chapter": {
            "id": chapter["id"],
            "title": chapter["title"],
            "desc": chapter["desc"],
            "dialogues": processed_dialogues,
            "choices": chapter.get("choices", [])
        },
        "can_trigger_usurper": can_trigger_usurper,
        "usurper_event": USURPER_EVENT if can_trigger_usurper else None,
        "is_total_blackened": game.state["is_total_blackened"],
        "total_collapse_event": TOTAL_COLLAPSE_EVENT if game.state["is_total_blackened"] else None
    }


@app.post("/api/story/choice")
def make_story_choice(req: StoryChoiceRequest):
    """提交主线选择，触发好感与交往机制"""
    idx = game.state.get("story_index", 0)
    if idx < len(STORY_CHAPTERS):
        chapter = STORY_CHAPTERS[idx]
        if req.choice_index < len(chapter["choices"]):
            choice = chapter["choices"][req.choice_index]
            tt = choice.get("target_type")
            aff = choice.get("aff_change", 5)

            if tt == "all":
                for cid in game.state["characters"]:
                    game.advance_affinity(cid, aff, "（全体关照）")
            elif tt == "crush":
                game.advance_affinity(game.state["crush_id"], aff, "（心动倾斜）")
            elif tt == "brother":
                game.state["system_logs"].append(f"哥哥 {game.state['brother_name']} 摸了摸你的头，心里十分欣慰。")
            elif tt == "dating_target":
                # 触发秘密交往
                crush_id = game.state["crush_id"]
                if choice.get("trigger_dating"):
                    game.start_dating(crush_id)
                else:
                    game.advance_affinity(crush_id, aff)

    # 章节推进
    game.state["story_index"] = min(len(STORY_CHAPTERS) - 1, game.state["story_index"] + 1)
    return {"success": True, "state": game.get_summary()}


@app.post("/api/usurper")
def trigger_usurper_choice(req: UsurperRequest):
    """上位剧情选择"""
    res = game.trigger_usurper(req.action)
    return res


@app.post("/api/dating/toggle")
def toggle_dating(req: DatingRequest):
    """快捷开启与某位成员的秘密交往 (用于试玩与测试多开/4人黑化)"""
    res = game.start_dating(req.char_id)
    return res


@app.post("/api/gacha/draw")
def draw_gacha():
    """抽卡一次"""
    card = game.draw_gacha()
    return {"success": True, "card": card, "state": game.get_summary()}


# 静态文件入口
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
