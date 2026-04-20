"""全局测试配置 - 加载.env环境变量"""

from pathlib import Path
from dotenv import load_dotenv

# 模块加载时立即执行，确保所有测试收集前环境变量已就绪
PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env", override=True)
