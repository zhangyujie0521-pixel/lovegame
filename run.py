# -*- coding: utf-8 -*-
"""
ASTERIA 顶流男团乙女恋爱游戏 - 一键启动器
"""

import socket
import uvicorn
from server import app

BIND_HOST = "0.0.0.0"


def find_available_port(start_port=8088, max_attempts=20):
    """检测可用端口，若被占用自动顺延"""
    for p in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((BIND_HOST, p))
                return p
            except OSError:
                continue
    return start_port


if __name__ == "__main__":
    port = find_available_port(8088)
    print("=================================================================")
    print("      💖 ASTERIA · 13人自制作顶流男团 乙女恋爱物语 启动成功 💖    ")
    print(f"      👉 本地访问网址: http://127.0.0.1:{port}/                   ")
    print(f"      👉 外网访问网址: http://47.237.71.105:{port}/               ")
    print("      🎲 特性：随机亲哥抽取 / 12抽1秘密暗恋者 / 11人零好感 / 3人地下情 / 4人黑化暴雷 ")
    print("=================================================================")

    uvicorn.run("server:app", host=BIND_HOST, port=port, reload=True)
