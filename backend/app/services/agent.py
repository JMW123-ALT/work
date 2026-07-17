"""兼容 facade — 勿在此添加新业务逻辑。

所有业务逻辑已迁移至 app/agents/ 下各子包。
本文件仅保留旧 import 路径的兼容性，避免现有调用链断裂。

已验证的存量引用（rg 确认）：
  - app/api/v1/agent.py:   from app.services.agent import Evidence, run_agent
  - tests/services/test_agent.py: from app.services.agent import Evidence, run_agent

所有上述引用均通过下方 re-export 保持可用。
"""

# noqa: F401
from app.agents.common.types import Evidence as Evidence  # noqa: F401
from app.agents.wenchuang.agent import WenchuangAgent as WenchuangAgent  # noqa: F401
from app.agents.wenchuang.agent import run_agent as run_agent  # noqa: F401
from app.agents.wenchuang.agent import run_agent_sync as run_agent_sync  # noqa: F401
