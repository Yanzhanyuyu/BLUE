"""人物检测跟踪系统主入口

提供命令行接口和便捷运行函数。

使用方式：
    命令行:
        python -m person_tracking.main --source video.mp4 --output output/tracked.mp4
        
    Python:
        from person_tracking import run_tracking
        run_tracking(source="video.mp4", output="output/tracked.mp4")
"""

import argparse
import sys
from pathlib import Path
from typing import Optional, Union

from .infra.config import Config, load_config
from .infra.logger import get_logger, setup_logger
from .core.pipeline import TrackingPipeline

logger = get_logger("main")


def create_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器

    Returns:
        参数解析器
    """
    parser = argparse.ArgumentParser(
        description="Person Detection and Tracking System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # 处理视频文件
    python -m person_tracking.main --source video.mp4 --output output/tracked.mp4
    
    # 使用摄像头实时处理
    python -m person_tracking.main --source 0 --show
    
    # 指定配置文件
    python -m person_tracking.main --source video.mp4 --config config/custom.yaml
    
    # 导出 CSV 日志
    python -m person_tracking.main --source video.mp4 --csv output/log.csv
        """,
    )

    # 必需参数
    parser.add_argument(
        "--source",
        "-s",
        type=str,
        required=True,
        help="视频源：文件路径或摄像头索引（如 0）",
    )

    # 可选参数
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="输出视频路径（默认不保存）",
    )

    parser.add_argument(
        "--csv",
        "-c",
        type=str,
        default=None,
        help="CSV 日志输出路径",
    )

    parser.add_argument(
        "--config",
        "-f",
        type=str,
        default=None,
        help="配置文件路径（YAML）",
    )

    parser.add_argument(
        "--show",
        action="store_true",
        help="实时显示处理结果",
    )

    parser.add_argument(
        "--model",
        "-m",
        type=str,
        default=None,
        help="模型路径（覆盖配置文件）",
    )

    parser.add_argument(
        "--device",
        "-d",
        type=str,
        choices=["cuda", "cpu", "mps"],
        default=None,
        help="推理设备（覆盖配置文件）",
    )

    parser.add_argument(
        "--confidence",
        "-conf",
        type=float,
        default=None,
        help="检测置信度阈值（覆盖配置文件）",
    )

    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="静默模式，不显示进度",
    )

    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version="%(prog)s 1.0.0",
    )

    return parser


def run_tracking(
    source: Union[str, int, Path],
    output: Optional[str | Path] = None,
    csv: Optional[str | Path] = None,
    config: Optional[str | Path] = None,
    show: bool = False,
    model: Optional[str] = None,
    device: Optional[str] = None,
    confidence: Optional[float] = None,
    quiet: bool = False,
) -> dict:
    """运行人物检测跟踪

    便捷函数，用于 Python 代码调用。

    Args:
        source: 视频源（文件路径或摄像头索引）
        output: 输出视频路径
        csv: CSV 日志路径
        config: 配置文件路径
        show: 是否实时显示
        model: 模型路径（覆盖配置）
        device: 推理设备（覆盖配置）
        confidence: 置信度阈值（覆盖配置）
        quiet: 静默模式

    Returns:
        处理统计信息

    Example:
        >>> stats = run_tracking(
        ...     source="video.mp4",
        ...     output="output/tracked.mp4",
        ...     csv="output/log.csv",
        ... )
        >>> print(f"Processed {stats['total_frames']} frames")
    """
    # 加载配置
    cfg = load_config(config)

    # 应用命令行覆盖
    if model:
        cfg.detector.model_path = model
    if device:
        cfg.detector.device = device
    if confidence:
        cfg.detector.confidence_threshold = confidence

    # 创建处理管道
    pipeline = TrackingPipeline(cfg)

    # 定义进度回调
    def progress_callback(current: int, total: int) -> None:
        if not quiet and total > 0:
            percent = current / total * 100
            bar_len = 40
            filled = int(bar_len * current / total)
            bar = "█" * filled + "-" * (bar_len - filled)
            print(f"\r进度: [{bar}] {percent:.1f}% ({current}/{total})", end="")
            if current >= total:
                print()  # 换行

    # 运行处理
    stats = pipeline.run(
        source=source,
        output_path=output,
        csv_path=csv,
        show=show,
        progress_callback=None if quiet else progress_callback,
    )

    return stats


def main() -> int:
    """主函数

    命令行入口点。

    Returns:
        退出码（0 表示成功）
    """
    # 解析参数
    parser = create_parser()
    args = parser.parse_args()

    try:
        # 设置日志
        setup_logger(level="WARNING" if args.quiet else "INFO")

        # 处理 source（可能是摄像头索引）
        source: Union[str, int]
        try:
            # 尝试解析为整数（摄像头索引）
            source = int(args.source)
        except ValueError:
            # 文件路径
            source = args.source

        # 运行跟踪
        stats = run_tracking(
            source=source,
            output=args.output,
            csv=args.csv,
            config=args.config,
            show=args.show,
            model=args.model,
            device=args.device,
            confidence=args.confidence,
            quiet=args.quiet,
        )

        # 输出统计信息
        if not args.quiet:
            print("\n" + "=" * 50)
            print("处理完成!")
            print(f"  总帧数: {stats['total_frames']}")
            print(f"  处理时间: {stats['elapsed_time']:.2f} 秒")
            print(f"  平均帧率: {stats['avg_fps']:.1f} FPS")
            print(f"  轨迹数量: {stats['trajectories_created']}")
            if args.output:
                print(f"  输出视频: {args.output}")
            if args.csv:
                print(f"  CSV 日志: {args.csv}")
            print("=" * 50)

        return 0

    except KeyboardInterrupt:
        print("\n用户中断")
        return 1
    except Exception as e:
        logger.error(f"运行错误: {e}")
        print(f"错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
