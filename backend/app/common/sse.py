"""全项目共享 SSE 格式化工具。

调用方（api/v1/agent.py, api/v1/websearch.py）均从此导入，
保证整个项目 SSE 格式完全一致，不再各自维护私有实现。
"""

import json


def sse_event(event: str, data: dict) -> str:
    """把事件名和数据字典序列化为 SSE 报文。

    格式：``event: {event}\\ndata: {payload}\\n\\n``

    Args:
        event: SSE 事件名，如 ``"delta"``、``"final"``、``"done"``。
        data:  要序列化为 JSON 的数据字典。

    Returns:
        符合 SSE 规范的字符串，以 ``\\n\\n`` 结尾。
    """
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"
