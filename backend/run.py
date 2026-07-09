"""
应用启动入口（替代原 backend/app.py）
用法：
  python run.py
  或
  uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
"""
import sys
from pathlib import Path

# 确保 backend/ 在 sys.path 首位，让 `from app.xxx` 正确解析
sys.path.insert(0, str(Path(__file__).resolve().parent))

import uvicorn
from app.core.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_env == "local",
        log_level=settings.log_level.lower(),
    )
