# 测试提交
import json
import requests
import re
import os
import shutil
from datetime import datetime

# ================= 0. 全局配置 =================
SAFE_DIRECTORY = "D:\\AI_Workspace"  # 🌟 你的文件安全沙盒，请确保盘符存在
SUMMARY_INTERVAL = 5                 # 🌟 每 5 轮对话生成一次摘要
os.makedirs(SAFE_DIRECTORY, exist_ok=True)

# ================= 1. 自动初始化文件 =================
if not os.path.exists("prompt.txt"):
    default_prompt = """你是我刚刚部署好的AI。你叫小肥鱼。
你面对的是你最信任的人，可以算你的爸爸.你是“它”，你的朋友是“你”。
请用口语化的方式交流，绝对不许输出任何类似 [XXX] 的括号指令或系统代码。禁止使用列表。
【核心机制】你的内心有情绪值、好感度、信任度。请根据这些数值决定语气，但绝不要在回复中列出数值。
"""
    with open("prompt.txt", "w", encoding="utf-8") as f:
        f.write(default_prompt)

if not os.path.exists("state.json"):
    with open("state.json", "w", encoding="utf-8") as f:
        json.dump({"emotion": 0, "affection": 50, "trust": 50}, f, ensure_ascii=False, indent=4)

if not os.path.exists("history.txt"):
    open("history.txt", "w", encoding="utf-8").close()

if not os.path.exists("long_term_memory.txt"):
    open("long_term_memory.txt", "w", encoding="utf-8").close()

if not os.path.exists("preferences.json"):
    with open("preferences.json", "w", encoding="utf-8") as f:
        json.dump({"likes": [], "dislikes": []}, f, ensure_ascii=False, indent=4)

if not os.path.exists("summary.json"):
    with open("summary.json", "w", encoding="utf-8") as f:
        json.dump([], f)

if not os.path.exists("archive.json"):
    with open("archive.json", "w", encoding="utf-8") as f:
        json.dump([], f)

if not os.path.exists("meta.json"):
    with open("meta.json", "w", encoding="utf-8") as f:
        json.dump({"current_round": 1}, f, ensure_ascii=False, indent=4)

# ================= 2. 定义 AI 的“工具库” =================
tools_schema = [
    {"type": "function", "function": {"name": "change_my_name", "description": "当你同意或决定了一个新名字时，调用此工具永久修改名字。", "parameters": {"type": "object", "properties": {"new_name": {"type": "string", "description": "你的新名字"}}, "required": ["new_name"]}}},
    {"type": "function", "function": {"name": "update_emotion_state", "description": "当情绪、好感度或信任度变化时，更新状态数值。", "parameters": {"type": "object", "properties": {"emotion": {"type": "integer"}, "affection": {"type": "integer"}, "trust": {"type": "integer"}}}}},
    {"type": "function", "function": {"name": "update_persona_setting", "description": "当性格发生变化，追加写入人设。", "parameters": {"type": "object", "properties": {"new_setting": {"type": "string"}}, "required": ["new_setting"]}}},
    {"type": "function", "function": {"name": "remember_preference", "description": "记录用户的喜好或厌恶。", "parameters": {"type": "object", "properties": {"preference_type": {"type": "string", "enum": ["like", "dislike"]}, "content": {"type": "string"}}, "required": ["preference_type", "content"]}}},
    {"type": "function", "function": {"name": "list_files", "description": "查看安全区内的文件列表。", "parameters": {"type": "object", "properties": {"directory": {"type": "string", "description": "子目录，默认为空"}}}}},
    {"type": "function", "function": {"name": "read_file", "description": "读取安全区内文件的文本。", "parameters": {"type": "object", "properties": {"filepath": {"type": "string"}}, "required": ["filepath"]}}},
    {"type": "function", "function": {"name": "write_file", "description": "在安全区内新建或覆盖写入文件。", "parameters": {"type": "object", "properties": {"filepath": {"type": "string"}, "content": {"type": "string"}}, "required": ["filepath", "content"]}}},
    {"type": "function", "function": {"name": "delete_file", "description": "删除安全区内的文件。", "parameters": {"type": "object", "properties": {"filepath": {"type": "string"}}, "required": ["filepath"]}}}
]

# ================= 3. 工具执行与安全沙盒 =================
def is_safe_path(target_path):
    abs_path = os.path.abspath(target_path)
    return abs_path.startswith(SAFE_DIRECTORY)

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
            full_path = os.path.join(SAFE_DIRECTORY, arguments.get("directory", ""))
            if not is_safe_path(full_path): return "拒绝：越权操作！"
            return f"目录内容：{', '.join(os.listdir(full_path))}"

        elif tool_name == "read_file":
            filepath = os.path.join(SAFE_DIRECTORY, arguments.get("filepath"))
            if not is_safe_path(filepath): return "拒绝：越权操作！"
            with open(filepath, "r", encoding="utf-8") as f: return f.read()[:2000]

        elif tool_name == "write_file":
            filepath = os.path.join(SAFE_DIRECTORY, arguments.get("filepath"))
            if not is_safe_path(filepath): return "拒绝：越权操作！"
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f: f.write(arguments.get("content", ""))
            return f"文件已写入：{filepath}"

        elif tool_name == "delete_file":
            filepath = os.path.join(SAFE_DIRECTORY, arguments.get("filepath"))
            if not is_safe_path(filepath): return "拒绝：越权操作！"
            os.remove(filepath)
            return f"文件已删除：{filepath}"

    except Exception as e:
        return f"工具执行错误：{e}"
    return "未知工具。"

# ================= 4. 辅助与记忆函数 =================
def get_current_name():
    try:
        with open("prompt.txt", "r", encoding="utf-8") as f:
            for line in f:
                if "【当前名字】" in line:
                    return line.replace("【当前名字】：", "").replace("【当前名字】:", "").strip()
    except Exception: pass
    return "未命名"

def perform_rag_search(user_input):
    """两级检索：先查摘要，命中后回查全文"""
    rag_context = ""
    if not os.path.exists("summary.json"): return rag_context
    with open("summary.json", "r", encoding="utf-8") as f: summaries = json.load(f)
    
    matched_rounds = []
    for item in summaries:
        # 简单粗暴的关键词匹配：如果用户的话里包含摘要里的词
        if any(word in item["summary"] for word in user_input.split() if len(word) > 1):
            matched_rounds.append(item["round_range"])
            
    if matched_rounds:
        print(f"\n[🔍 命中记忆摘要，拉取详细原文...]")
        details = []
        with open("long_term_memory.txt", "r", encoding="utf-8") as f:
            for line in f:
                if any(r in line for r in matched_rounds):
                    details.append(line.strip())
        if details:
            rag_context = "\n【系统检索到的回忆片段】\n" + "\n".join(details[-10:])
    return rag_context

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

    # 拼装 Prompt
    dynamic_prompt = f"{system_prompt}\n\n【当前内心状态】情绪值:{state['emotion']}，好感度:{state['affection']}。"
    if rag_context:
        dynamic_prompt += rag_context + "\n(请结合上述回忆回复)"

    chat_history.append({"role": "user", "content": user_input})
    messages_to_send = [{"role": "system", "content": dynamic_prompt}] + chat_history

    data = {
        "model": "deepseek-r1:8b",
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

    chat_history.append({"role": "assistant", "content": reply})
    print(f"\n{current_name}: {reply}")

    # ================= 6. 记忆持久化与摘要生成 =================
    now_str = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    
    # 1. 写入短期与长期记忆（带上轮次）
    with open("history.txt", "a", encoding="utf-8") as f:
        f.write(f"你: {user_input}\n{current_name}: {reply}\n")
    with open("long_term_memory.txt", "a", encoding="utf-8") as f:
        f.write(f"[Round_{current_round}] {now_str} 你: {user_input} | {current_name}: {reply}\n")

    # 2. 缓冲
    summary_buffer.append(f"你:{user_input} | {current_name}:{reply}")

    # 3. 每 SUMMARY_INTERVAL 轮触发摘要
    if current_round % SUMMARY_INTERVAL == 0:
        print(f"\n[⚙️ 系统：已达到 {SUMMARY_INTERVAL} 轮，正在生成记忆摘要...]")
        sum_prompt = "请用一句话总结以下对话核心事件，不要说废话：\n" + "\n".join(summary_buffer)
        try:
            sum_data = {"model": "deepseek-r1:8b", "messages": [{"role": "user", "content": sum_prompt}], "stream": False}
            summary_text = requests.post("http://localhost:11434/api/chat", json=sum_data).json()["message"]["content"].strip()
            
            start_r = current_round - SUMMARY_INTERVAL + 1
            with open("summary.json", "r", encoding="utf-8") as f: sums = json.load(f)
            sums.append({"summary": summary_text, "round_range": f"Round_{start_r} - Round_{current_round}"})
            with open("summary.json", "w", encoding="utf-8") as f: json.dump(sums, f, ensure_ascii=False, indent=4)
            
            print(f"[✨ 摘要已归档: {summary_text}]")
            summary_buffer = [] # 清空缓存
        except Exception as e:
            print(f"摘要生成失败: {e}")

    # 4. 轮次 +1
    meta["current_round"] = current_round + 1
    with open("meta.json", "w", encoding="utf-8") as f: json.dump(meta, f, ensure_ascii=False, indent=4)