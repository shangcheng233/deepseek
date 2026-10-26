# 测试提交
import json
import requests
import re
import os
import shutil
from datetime import datetime

# ================= 0. 全局配置 =================
SAFE_DIRECTORIES = ["A:", ]  # 🌟 你的多个文件安全沙盒路径列表
SUMMARY_INTERVAL = 5                 # 🌟 每 5 轮对话生成一次摘要
for d in SAFE_DIRECTORIES:
    os.makedirs(d, exist_ok=True)

from config import init_files
from memory import clean_expired_raw_memory

# 初始化所有文件与目录
init_files()
# 启动检查并清理超过5年的原始记忆
clean_expired_raw_memory()


# ================= 2. 定义 AI 的“工具库” =================
tools_schema = [
    {"type": "function", "function": {"name": "change_my_name", "description": "当你同意或决定了一个新名字时，调用此工具永久修改名字。", "parameters": {"type": "object", "properties": {"new_name": {"type": "string", "description": "你的新名字"}}, "required": ["new_name"]}}},
    {"type": "function", "function": {"name": "update_emotion_state", "description": "当情绪、好感度或信任度变化时，更新状态数值。", "parameters": {"type": "object", "properties": {"emotion": {"type": "integer"}, "affection": {"type": "integer"}, "trust": {"type": "integer"}}}}},
    {"type": "function", "function": {"name": "update_persona_setting", "description": "当性格发生变化，追加写入人设。", "parameters": {"type": "object", "properties": {"new_setting": {"type": "string"}}, "required": ["new_setting"]}}},
    {"type": "function", "function": {"name": "remember_preference", "description": "记录用户的喜好或厌恶。", "parameters": {"type": "object", "properties": {"preference_type": {"type": "string", "enum": ["like", "dislike"]}, "content": {"type": "string"}}, "required": ["preference_type", "content"]}}},
    {"type": "function", "function": {"name": "list_files", "description": "查看安全区内的文件列表。", "parameters": {"type": "object", "properties": {"directory": {"type": "string", "description": "子目录，默认为空"}}}}},
    {"type": "function", "function": {"name": "read_file", "description": "【必须调用】读取指定路径文件的文本内容。当你被要求查看、读取或检查文件时，必须立刻调用此工具。", "parameters": {"type": "object", "properties": {"filepath": {"type": "string", "description": "文件的路径，例如 A:\\测试\\111.txt"}}, "required": ["filepath"]}}},
    {"type": "function", "function": {"name": "write_file", "description": "在安全区内新建或覆盖写入文件。", "parameters": {"type": "object", "properties": {"filepath": {"type": "string"}, "content": {"type": "string"}}, "required": ["filepath", "content"]}}},
    {"type": "function", "function": {"name": "delete_file", "description": "删除安全区内的文件。", "parameters": {"type": "object", "properties": {"filepath": {"type": "string"}}, "required": ["filepath"]}}}
]

# ================= 3. 工具执行与安全沙盒 =================
def is_safe_path(target_path):
    abs_path = os.path.abspath(target_path)
    return any(abs_path.startswith(os.path.abspath(d)) for d in SAFE_DIRECTORIES)

def execute_tool(tool_name, arguments):
    try:
        if tool_name == "change_my_name":
            new_name = arguments.get("new_name")
            with open("prompt.txt", "a", encoding="utf-8") as f:
                f.write(f"\n【系统记录】：你已通过工具将名字修改为：{new_name}。")
            return f"成功，名字已修改为 {new_name}。"
            
        elif tool_name == "update_emotion_state":
            with open("state.json", "r", encoding="utf-8") as f: state = json.load(f)
            if "emotion" in arguments: state["emotion"] = max(-100, min(100, state.get("emotion", 0) + arguments["emotion"]))
            if "affection" in arguments: state["affection"] = max(0, min(100, state.get("affection", 50) + arguments["affection"]))
            if "trust" in arguments: state["trust"] = max(0, min(100, state.get("trust", 50) + arguments["trust"]))
            with open("state.json", "w", encoding="utf-8") as f: json.dump(state, f, ensure_ascii=False, indent=4)
            return f"状态已更新。"
            
        elif tool_name == "update_persona_setting":
            with open("prompt.txt", "a", encoding="utf-8") as f: f.write(f"\n【自我反思】：{arguments.get('new_setting')}")
            return "人设已更新。"
            
        elif tool_name == "remember_preference":
            p_type, content = arguments.get("preference_type"), arguments.get("content")
            with open("preferences.json", "r", encoding="utf-8") as f: prefs = json.load(f)
            if p_type == "like" and content not in prefs["likes"]: prefs["likes"].append(content)
            elif p_type == "dislike" and content not in prefs["dislikes"]: prefs["dislikes"].append(content)
            with open("preferences.json", "w", encoding="utf-8") as f: json.dump(prefs, f, ensure_ascii=False, indent=4)
            return "偏好已记录。"

        # --- 文件操作系列 ---
        elif tool_name == "list_files":
            sub_dir = arguments.get("directory", "")
            # 如果指定了绝对路径或包含盘符，尝试直接组合；否则检查各个沙盒
            target_path = arguments.get("filepath") or sub_dir
            # 支持在多个沙盒中查找或指定子目录
            results = []
            for base_d in SAFE_DIRECTORIES:
                full_path = os.path.join(base_d, sub_dir)
                if os.path.exists(full_path) and is_safe_path(full_path):
                    try:
                        results.append(f"[{base_d}]: {', '.join(os.listdir(full_path))}")
                    except Exception:
                        pass
            if results:
                return "目录内容：\n" + "\n".join(results)
            return "拒绝：目录不存在或越权操作！"

        elif tool_name == "read_file":
            req_path = arguments.get("filepath")
            filepath = None
            for base_d in SAFE_DIRECTORIES:
                p = os.path.join(base_d, req_path)
                if os.path.exists(p) and is_safe_path(p):
                    filepath = p
                    break
            if not filepath:
                # 尝试直接判断是否是绝对路径且安全
                if os.path.exists(req_path) and is_safe_path(req_path):
                    filepath = req_path
            if not filepath or not is_safe_path(filepath): return "拒绝：文件不存在或越权操作！"
            with open(filepath, "r", encoding="utf-8") as f: return f.read()[:2000]

        elif tool_name == "write_file":
            req_path = arguments.get("filepath")
            # 默认写入第一个沙盒，或者如果req_path带了绝对路径/相对某个沙盒存在则用对应沙盒
            filepath = None
            for base_d in SAFE_DIRECTORIES:
                p = os.path.join(base_d, req_path)
                if is_safe_path(p):
                    filepath = p
                    break
            if not filepath:
                filepath = os.path.join(SAFE_DIRECTORIES[0], req_path)
            if not is_safe_path(filepath): return "拒绝：越权操作！"
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f: f.write(arguments.get("content", ""))
            return f"文件已写入：{filepath}"

        elif tool_name == "delete_file":
            req_path = arguments.get("filepath")
            filepath = None
            for base_d in SAFE_DIRECTORIES:
                p = os.path.join(base_d, req_path)
                if os.path.exists(p) and is_safe_path(p):
                    filepath = p
                    break
            if not filepath:
                if os.path.exists(req_path) and is_safe_path(req_path):
                    filepath = req_path
            if not filepath or not is_safe_path(filepath): return "拒绝：文件不存在或越权操作！"
            os.remove(filepath)
            return f"文件已删除：{filepath}"

    except Exception as e:
        return f"工具执行错误：{e}"
    return "未知工具。"

# ================= 4. 辅助与记忆函数 =================
from memory import get_current_name, perform_rag_search, append_memory, process_tiered_memory

# ================= 5. 主循环 =================
chat_history = []
summary_buffer = [] # 用于缓存未总结的对话

while True:
    # 读状态
    with open("meta.json", "r", encoding="utf-8") as f: meta = json.load(f)
    current_round = meta.get("current_round", 1)
    
    current_name = get_current_name()
    with open("prompt.txt", "r", encoding="utf-8") as f: system_prompt = f.read()
    with open("state.json", "r", encoding="utf-8") as f: state = json.load(f)

    user_input = input(f"\n你: ")
    if user_input.lower() == 'exit': break

    # 🌟 检索增强（RAG）
    rag_context = perform_rag_search(user_input)

    # 拼装 Prompt14b
    dynamic_prompt = f"{system_prompt}\n\n【当前内心状态】情绪值:{state['emotion']}，好感度:{state['affection']}。"
    if rag_context:
        dynamic_prompt += rag_context + "\n(请结合上述回忆回复)"

    chat_history.append({"role": "user", "content": user_input})
    messages_to_send = [{"role": "system", "content": dynamic_prompt}] + chat_history

    data = {
        "model": "deepseek-r1:14b",
        "messages": messages_to_send,
        "stream": False,
        "tools": tools_schema
    }

    print("正在思考...")
    try:
        response = requests.post("http://localhost:11434/api/chat", json=data)
        message = response.json()["message"]
    except Exception as e:
        print(f"[网络错误]: {e}"); chat_history.pop(); continue

    # 处理工具调用
    if "tool_calls" in message and message["tool_calls"]:
        tool_call = message["tool_calls"][0]
        fn_name = tool_call["function"]["name"]
        args = tool_call["function"]["arguments"]
        if isinstance(args, str):
            try: args = json.loads(args)
            except: pass
            
        print(f"\n[⚙️ 系统：后台调用工具 {fn_name}]")
        tool_result = execute_tool(fn_name, args)
        
        chat_history.append(message)
        chat_history.append({"role": "tool", "content": tool_result})
        data["messages"] = [{"role": "system", "content": dynamic_prompt}] + chat_history
        try:
            reply = requests.post("http://localhost:11434/api/chat", json=data).json()["message"]["content"]
        except: reply = "（脑子卡壳）"
        current_name = get_current_name()
    else:
        reply = message["content"]

    # 过滤掉回复中形如 (...)、[...] 的心理活动、动作动作或工具说明
    reply = re.sub(r'\（.*?\）|\(.*?\)|\[.*?\]', '', reply).strip()

    chat_history.append({"role": "assistant", "content": reply})
    print(f"\n{current_name}: {reply}")

    # ================= 6. 记忆持久化与分层归档管理 =================
    append_memory(user_input, reply, current_round)

    # 2. 缓冲
    summary_buffer.append(f"你:{user_input} | {current_name}:{reply}")

    # 3. 处理分层记忆（short 摘要生成与 5 年过期归档）
    process_tiered_memory(current_round, summary_buffer)

    # 4. 轮次 +1
    meta["current_round"] = current_round + 1
    with open("meta.json", "w", encoding="utf-8") as f: json.dump(meta, f, ensure_ascii=False, indent=4)