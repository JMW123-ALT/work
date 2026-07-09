"""命令行入口逻辑。

用于本地快速运行 Agent，不需要启动 FastAPI 服务。
"""

from __future__ import annotations

import argparse
import asyncio

from .graph import run_agent


def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""

    parser = argparse.ArgumentParser(description="Run the Wenchuang Agent demo.")
    parser.add_argument("query", nargs="*", help="文创需求，例如：敦煌保温杯文创，偏国潮厚重风")
    return parser


async def async_main() -> None:
    """异步主函数：解析 query 并运行完整 Agent。"""

    args = build_parser().parse_args()
    query = " ".join(args.query).strip() or "敦煌保温杯文创，偏国潮厚重风，输出小红书文案"
    result = await run_agent(query)
    print(result.final_answer)


def main() -> None:
    """同步入口，供 `wenchuang_agent.py` 调用。"""

    asyncio.run(async_main())


if __name__ == "__main__":
    main()
