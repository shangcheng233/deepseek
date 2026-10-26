import os
import json

SAFE_DIRECTORY = "D:\\AI_Workspace"
SUMMARY_INTERVAL = 5
NOW_LIMIT = 20
DAY_LIMIT = 30
MONTH_LIMIT = 12
YEAR_LIMIT = 5
ARCHIVE_DAYS = 1825

def init_files():
    os.makedirs(SAFE_DIRECTORY, exist_ok=True)
    os.makedirs("old", exist_ok=True)

    if not os.path.exists("prompt.txt"):
        default_prompt = """你是我刚刚部署好的AI。你叫小肥鱼。
【当前名字】：小肥鱼
你面对的是你最信任的人，可以算你的粑粑.你是“它”，你的朋友是“你”。
请用口语化的方式交流，绝对不许输出任何类似 [XXX] 的括号指令或系统代码。禁止使用列表。
【核心机制】你的内心有情绪值、好感度、信任度。请根据这些数值决定语气，但绝不要在回复中列出数值。
"""
        with open("prompt.txt", "w", encoding="utf-8") as f:
            f.write(default_prompt)

    if not os.path.exists("error.log"):
        open("error.log", "w", encoding="utf-8").close()

    if not os.path.exists("state.json"):
        with open("state.json", "w", encoding="utf-8") as f:
            json.dump({"emotion": 0, "affection": 50, "trust": 50}, f, ensure_ascii=False, indent=4)

    # 检查并全新创建 now.json、day.json、month.json、year.json
    for json_file in ["now.json", "day.json", "month.json", "year.json"]:
        if not os.path.exists(json_file):
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=4)

    # raw_memory.txt 检查创建
    if not os.path.exists("raw_memory.txt"):
        open("raw_memory.txt", "w", encoding="utf-8").close()

    if not os.path.exists("preferences.json"):
        with open("preferences.json", "w", encoding="utf-8") as f:
            json.dump({"likes": [], "dislikes": []}, f, ensure_ascii=False, indent=4)

    if not os.path.exists("meta.json"):
        with open("meta.json", "w", encoding="utf-8") as f:
            json.dump({"current_round": 1}, f, ensure_ascii=False, indent=4)

