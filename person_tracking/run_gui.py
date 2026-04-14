"""GUI 启动脚本

直接启动 GUI，避免通过 src 包导入时触发 PyTorch/YOLO 加载。

使用方法:
    python run_gui.py
"""

import sys
from pathlib import Path

# 添加 src 到路径，但不触发 src/__init__.py 的导入
sys.path.insert(0, str(Path(__file__).parent / "src"))

# 直接从 gui 模块导入，绕过 src/__init__.py
from gui.app import run_gui

if __name__ == "__main__":
    sys.exit(run_gui())
