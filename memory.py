import os
import json
import requests
from datetime import datetime, timedelta
from logger import log_error
from config import SUMMARY_INTERVAL, NOW_LIMIT, DAY_LIMIT, MONTH_LIMIT, YEAR_LIMIT, ARCHIVE_DAYS

def get_current_name():
    try:
        with open("prompt.txt", "r", encoding="utf-8") as f:
            for line in f:
                if "【当前名字】" in line:
                    parts = line.split("：")
                    if len(parts) > 1:
                        return parts[1].strip()
                    parts_colon = line.split(":")
                    if len(parts_colon) > 1:
                        return parts_colon[1].strip()
    except Exception as e:
        log_error(f"[get_current_name Error]: {e}")
    return "小肥鱼"

def init_memory_hierarchy():
    """初始化所有记忆文件和老旧归档文件夹(old)"""
    os.makedirs("old", exist_ok=True)
    for json_file in ["now.json", "day.json", "month.json", "year.json"]:
        if not os.path.exists(json_file):
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=4)
    if not os.path.exists("raw_memory.txt"):
        open("raw_memory.txt", "w", encoding="utf-8").close()

def clean_expired_raw_memory():
    """每次启动检查，凡是距今超过 1825 天（5年）的行，剪切并存入 old/archive_raw_[年份].txt，原文件删除对应行。"""
    init_memory_hierarchy()
    try:
        if not os.path.exists("raw_memory.txt"):
            return
        current_time = datetime.now()
        retained_lines = []
        year_to_expired_lines = {}

        with open("raw_memory.txt", "r", encoding="utf-8") as f:
            for line in f:
                matched_time = None
                try:
                    import re
                    m = re.search(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]', line)
                    if m:
                        ts_str = m.group(1)
                        line_time = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                        if (current_time - line_time).days > ARCHIVE_DAYS:
                            matched_time = line_time
                except Exception:
                    pass

                if matched_time:
                    yr = matched_time.strftime("%Y")
                    if yr not in year_to_expired_lines:
                        year_to_expired_lines[yr] = []
                    year_to_expired_lines[yr].append(line.strip())
                else:
                    retained_lines.append(line)

        if year_to_expired_lines:
            for yr, lines in year_to_expired_lines.items():
                archive_path = os.path.join("old", f"archive_raw_{yr}.txt")
                with open(archive_path, "a", encoding="utf-8") as of:
                    of.write("\n".join(lines) + "\n")
            with open("raw_memory.txt", "w", encoding="utf-8") as f:
                f.writelines(retained_lines)
    except Exception as e:
        log_error(f"[clean_expired_raw_memory Error]: {e}")

def append_memory(user_input, reply, current_round):
    """每次对话将内容记录到 raw_memory.txt，每行带 [Round_X] [YYYY-MM-DD HH:MM:SS]"""
    init_memory_hierarchy()
    now_str = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    line_str = f"[Round_{current_round}] [{now_str}] 你: {user_input} | 小肥鱼: {reply}\n"
    with open("raw_memory.txt", "a", encoding="utf-8") as f:
        f.write(line_str)


def process_tiered_memory(current_round, summary_buffer):
    """
    分层记忆归档与压缩机制：
    1. 每5轮对话触发摘要，存入 short.json (带对话时间戳、总结时间戳、轮次范围)。
    2. 检查 long.txt 中的记录，若有时间跨度超过 5 年的记录：
       - 提炼并归档到 long_long.json (高层长期归档库)。
       - 超过 5 年的原始记录切割存入 old/ 文件夹下的归档文件中。
    """
    init_memory_hierarchy()
    now_str = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    
    # --- 1. 处理 short.json 摘要（每 5 轮） ---
    if current_round > 0 and current_round % 5 == 0 and summary_buffer:
        print(f"\n[⚙️ 系统：已达到 5 轮，正在生成分层记忆摘要 (short)...]")
        sum_prompt = "请用一句话精炼总结以下对话核心事件，不要说废话：\n" + "\n".join(summary_buffer)
        try:
            import requests
            sum_data = {"model": "deepseek-r1:14b", "messages": [{"role": "user", "content": sum_prompt}], "stream": False}
            summary_text = requests.post("http://localhost:11434/api/chat", json=sum_data).json()["message"]["content"].strip()
            
            start_r = current_round - 4
            summary_entry = {
                "summary": summary_text,
                "round_range": f"Round_{start_r} - Round_{current_round}",
                "dialogue_timestamp": now_str,
                "summary_timestamp": now_str,
                "rounds": [r for r in range(start_r, current_round + 1)]
            }
            
            with open("short.json", "r", encoding="utf-8") as f:
                shorts = json.load(f)
            shorts.append(summary_entry)
            
            if len(shorts) > 100:
                old_shorts = shorts[:50]
                shorts = shorts[50:]
                with open("long.txt", "a", encoding="utf-8") as lf:
                    lf.write(f"\n--- [长期摘要归档 {now_str}] ---\n" + json.dumps(old_shorts, ensure_ascii=False) + "\n")
            
            with open("short.json", "w", encoding="utf-8") as f:
                json.dump(shorts, f, ensure_ascii=False, indent=4)
                
            print(f"[✨ 摘要已归档至 short.json: {summary_text}]")
            summary_buffer.clear()
        except Exception as e:
            log_error(f"[Summary Generation Error]: {e}")

    # --- 2. 检查 5 年过期归档机制 (long -> long_long & old/) ---
    try:
        if os.path.exists("long.txt"):
            current_time = datetime.now()
            retained_lines = []
            expired_lines = []
            
            with open("long.txt", "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("[") and "]" in line:
                        ts_str = line[1:line.index("]")]
                        try:
                            line_time = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                            if (current_time - line_time).days > 1826:
                                expired_lines.append(line.strip())
                                continue
                        except Exception:
                            pass
                    retained_lines.append(line)
            
            if expired_lines:
                print(f"\n[⚙️ 系统：检测到超过 5 年的长期记忆，正在归档至 long_long 与 old/...] ")
                if os.path.exists("long_long.json"):
                    with open("long_long.json", "r", encoding="utf-8") as llf:
                        long_long_data = json.load(llf)
                else:
                    long_long_data = []
                
                long_long_entry = {
                    "archive_timestamp": now_str,
                    "content": expired_lines
                }
                long_long_data.append(long_long_entry)
                with open("long_long.json", "w", encoding="utf-8") as llf:
                    json.dump(long_long_data, llf, ensure_ascii=False, indent=4)
                
                year_str = current_time.strftime("%Y")
                old_file_path = os.path.join("old", f"archive_{year_str}.txt")
                with open(old_file_path, "a", encoding="utf-8") as of:
                    of.write(f"\n=== 过期记忆归档 ({now_str}) ===\n" + "\n".join(expired_lines) + "\n")
                
                with open("long.txt", "w", encoding="utf-8") as f:
                    f.writelines(retained_lines)
    except Exception as e:
        log_error(f"[Five-Year Archive Error]: {e}")

