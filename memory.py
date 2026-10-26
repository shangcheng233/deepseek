import json
from logger import log_error

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

def perform_rag_search(user_input):
    """修正后的中文兼容 RAG 检索：支持子串包含匹配"""
    rag_context = ""
    if not os.path.exists("summary.json"): return rag_context
    try:
        with open("summary.json", "r", encoding="utf-8") as f: 
            summaries = json.load(f)
    except Exception as e:
        log_error(f"[RAG Load Summary Error]: {e}")
        return rag_context
    
    matched_rounds = []
    for item in summaries:
        summary_text = item.get("summary", "")
        if any(token in summary_text for token in [user_input[i:i+2] for i in range(len(user_input)-1)] if len(token.strip()) > 1):
            matched_rounds.append(item["round_range"])
        elif summary_text in user_input or user_input in summary_text:
            matched_rounds.append(item["round_range"])
            
    if matched_rounds:
        print(f"\n[🔍 命中记忆摘要，拉取详细原文...]")
        details = []
        try:
            with open("long_term_memory.txt", "r", encoding="utf-8") as f:
                for line in f:
                    if any(r in line for r in matched_rounds):
                        details.append(line.strip())
            if details:
                rag_context = "\n【系统检索到的回忆片段】\n" + "\n".join(details[-10:])
        except Exception as e:
            log_error(f"[RAG Read Memory Error]: {e}")
    return rag_context
