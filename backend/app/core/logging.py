"""
日志配置
优先使用 JSON 格式（便于日志采集），本地开发可切换为 text
"""
import logging
import sys
from typing import Any


def _make_formatter(log_format: str) -> logging.Formatter:
    if log_format == "json":
        try:
            from pythonjsonlogger import jsonlogger

            class _JsonFmt(jsonlogger.JsonFormatter):
                def add_fields(
                    self,
                    log_record: dict[str, Any],
                    record: logging.LogRecord,
                    message_dict: dict[str, Any],
                ) -> None:
                    super().add_fields(log_record, record, message_dict)
                    log_record["level"] = record.levelname
                    log_record["logger"] = record.name

            return _JsonFmt("%(timestamp)s %(level)s %(logger)s %(message)s")
        except ImportError:
            pass  # 没安装 python-json-logger，回退到 text
    return logging.Formatter("%(asctime)s  %(levelname)-8s  %(name)s  %(message)s")


def setup_logging() -> logging.Logger:
    # 延迟 import，避免循环（settings 模块本身不依赖 logging）
    from app.core.config import settings

    root = logging.getLogger()
    root.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_make_formatter(settings.log_format))
    root.addHandler(handler)

    # 降低第三方库噪音
    for noisy in ("uvicorn.access", "httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    return logging.getLogger("app")


logger = setup_logging()
