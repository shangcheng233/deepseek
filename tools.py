import os
import json
import re
from logger import log_error

SAFE_DIRECTORY = "D:\\AI_Workspace"

def is_safe_path(target_path):
    abs_path = os.path.abspath(target_path)
    return abs_path.startswith(SAFE_DIRECTORY)

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

def execute_tool(tool_name, arguments):
    try:
        if tool_name == "change_my_name":
            new_name = arguments.get("new_name")
            with open("prompt.txt", "r", encoding="utf-8") as f:
                content = f.read()
            if "【当前名字】" in content:
                content = re.sub(r"【当前名字】：.*", f"【当前名字】：{new_name}", content)
            else:
                content += f"\n【当前名字】：{new_name}\n"
            with open("prompt.txt", "w", encoding="utf-8") as f:
                f.write(content)
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
        err_msg = f"[Tool Error] {tool_name}: {e}"
        log_error(err_msg)
        return f"工具执行错误：{e}"
    return "未知工具。"
