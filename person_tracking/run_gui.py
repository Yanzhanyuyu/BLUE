"""GUI 启动脚本 - 标准 Python 包入口

使用方法:
    python run_gui.py
    python -m run_gui

重构说明:
- 移除了 sys.path.insert 绕过方式
- 改为标准 Python 包导入
- 错误处理更加完善
"""

import sys


def main() -> int:
    """主入口函数

    Returns:
        退出码 (0 表示成功)
    """
    try:
        # 标准导入方式 - 从 src.gui.app 导入 run_gui
        from src.gui.app import run_gui
        return run_gui()
    except ImportError as e:
        print(f"导入错误: {e}", file=sys.stderr)
        print("\n提示: 请确保从项目根目录运行此脚本", file=sys.stderr)
        print("  cd person_tracking", file=sys.stderr)
        print("  python run_gui.py", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"启动错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
