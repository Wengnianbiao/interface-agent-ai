"""LLM调用测试 - 验证invoke和stream"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env", override=True)

from backend.app.agents.llm import get_llm


def main():
    llm = get_llm()
    print(f"模型: {llm.model_name}\n")

    # 非流式
    print("=== invoke ===")
    result = llm.invoke("用一句话解释什么是Agent")
    print(result.content)

    # 流式
    print("\n=== stream ===")
    for chunk in llm.stream("用一句话说明Python的GIL"):
        content = chunk.content if hasattr(chunk, "content") else ""
        if content is not None and content != "":
            sys.stdout.write(content)
            sys.stdout.flush()
    print("\n=== done ===")


if __name__ == "__main__":
    main()
