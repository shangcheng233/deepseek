import os
from datetime import datetime

def log_error(err_msg):
    now_str = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    try:
        with open("error.log", "a", encoding="utf-8") as f:
            f.write(f"{now_str} {err_msg}\n")
    except Exception:
        pass
