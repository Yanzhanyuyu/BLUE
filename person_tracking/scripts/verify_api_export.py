#!/usr/bin/env python3
"""API 导出验证脚本

验证 README 中声明的 API 是否与源码实际导出一致。
用于 CI/CD 流程中确保文档与代码的同步。

使用方式:
    python scripts/verify_api_export.py

返回码:
    0: 验证通过
    1: 验证失败
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def verify_src_exports():
    """验证 src 模块的导出"""
    errors = []

    # 预期导出列表
    expected_exports = {
        "run_tracking": "函数",
    }

    # 实际导出
    try:
        import src
        actual_exports = getattr(src, "__all__", [])
        actual_attrs = [attr for attr in dir(src) if not attr.startswith("_")]
    except ImportError as e:
        errors.append(f"无法导入 src 模块: {e}")
        return errors

    # 验证预期导出
    for export_name, export_type in expected_exports.items():
        if export_name not in actual_attrs:
            errors.append(f"缺失导出: {export_name} ({export_type})")
        elif export_name not in actual_exports:
            errors.append(f"导出 {export_name} 未在 __all__ 中声明")

    return errors


def verify_gui_exports():
    """验证 src.gui 模块的导出"""
    errors = []

    # 预期导出列表
    expected_exports = {
        "run_gui": "函数",
        "MainWindow": "类",
        "VideoCanvas": "类",
    }

    # 实际导出
    try:
        from src.gui import __all__ as actual_exports
        from src import gui
        actual_attrs = [attr for attr in dir(gui) if not attr.startswith("_")]
    except ImportError as e:
        errors.append(f"无法导入 src.gui 模块: {e}")
        return errors

    # 验证预期导出
    for export_name, export_type in expected_exports.items():
        if export_name not in actual_attrs:
            errors.append(f"GUI 缺失导出: {export_name} ({export_type})")
        elif export_name not in actual_exports:
            errors.append(f"GUI 导出 {export_name} 未在 __all__ 中声明")

    return errors


def verify_cli_entry():
    """验证 CLI 入口是否可用"""
    errors = []

    try:
        from src.main import main
        if not callable(main):
            errors.append("CLI 入口 main() 不是可调用函数")
    except ImportError as e:
        errors.append(f"无法导入 CLI 入口: {e}")

    return errors


def main():
    """主验证函数"""
    all_errors = []

    print("=" * 60)
    print("API 导出验证")
    print("=" * 60)

    # 验证 src 模块导出
    print("\n[1] 验证 src 模块导出...")
    errors = verify_src_exports()
    if errors:
        all_errors.extend(errors)
        for err in errors:
            print(f"  ❌ {err}")
    else:
        print("  ✅ src 模块导出验证通过")

    # 验证 GUI 模块导出
    print("\n[2] 验证 src.gui 模块导出...")
    errors = verify_gui_exports()
    if errors:
        all_errors.extend(errors)
        for err in errors:
            print(f"  ❌ {err}")
    else:
        print("  ✅ src.gui 模块导出验证通过")

    # 验证 CLI 入口
    print("\n[3] 验证 CLI 入口...")
    errors = verify_cli_entry()
    if errors:
        all_errors.extend(errors)
        for err in errors:
            print(f"  ❌ {err}")
    else:
        print("  ✅ CLI 入口验证通过")

    # 总结
    print("\n" + "=" * 60)
    if all_errors:
        print(f"验证失败: {len(all_errors)} 个错误")
        print("=" * 60)
        return 1
    else:
        print("所有验证通过 ✅")
        print("=" * 60)
        return 0


if __name__ == "__main__":
    sys.exit(main())
