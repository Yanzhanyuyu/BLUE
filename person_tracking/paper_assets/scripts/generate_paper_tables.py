#!/usr/bin/env python
"""Generate paper tables for thesis experiments.

This script generates CSV tables for thesis, including:
1. System environment
2. Key parameters
3. CSV field description
4. Experiment video info
5. Performance summary (already exists)
6. Tracking summary (already exists)
"""

import csv
import platform
import sys
from pathlib import Path
import yaml


def generate_system_environment(output_path: Path) -> None:
    """Generate system environment table.

    Args:
        output_path: Path to save the CSV
    """
    # Get system information
    try:
        import torch

        cuda_available = torch.cuda.is_available()
        cuda_version = torch.version.cuda if cuda_available else "N/A"
        torch_version = torch.__version__
    except ImportError:
        cuda_available = False
        cuda_version = "N/A"
        torch_version = "N/A"

    try:
        import cv2

        opencv_version = cv2.__version__
    except ImportError:
        opencv_version = "N/A"

    try:
        import ultralytics

        ultralytics_version = ultralytics.__version__
    except ImportError:
        ultralytics_version = "N/A"

    # Get CPU and RAM info
    cpu_info = platform.processor()
    ram_info = f"{round(psutil.virtual_memory().total / (1024**3), 2)} GB"

    # Create table
    data = [
        ["OS", f"{platform.system()} {platform.release()}"],
        ["Python Version", f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"],
        ["PyTorch Version", torch_version],
        ["CUDA Version", cuda_version],
        ["Ultralytics Version", ultralytics_version],
        ["OpenCV Version", opencv_version],
        ["CPU", cpu_info],
        ["GPU", "Available" if cuda_available else "N/A"],
        ["RAM", ram_info],
        ["Model", "YOLOv11n"],
        ["Tracker", "ByteTrack"],
        ["Input Size", "640x640"],
        ["Confidence Threshold", "0.5"],
        ["IoU Threshold", "0.45"],
        ["Track Buffer", "30"],
        ["Trajectory Length", "50"],
    ]

    # Write to CSV
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Item", "Value"])
        writer.writerows(data)

    print(f"Saved: {output_path}")


def generate_key_parameters(config_path: Path, output_path: Path) -> None:
    """Generate key parameters table from config files.

    Args:
        config_path: Path to config directory
        output_path: Path to save the CSV
    """
    # Read default config
    default_config_path = config_path / "default.yaml"
    bytetrack_config_path = config_path / "bytetrack.yaml"

    data = []

    # Read default config
    if default_config_path.exists():
        with open(default_config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        # Extract detector parameters
        if "detector" in config:
            detector = config["detector"]
            data.append(["detector.model_path", detector.get("model_path", "N/A"), "YOLOv11 model path"])
            data.append(
                ["detector.confidence_threshold", detector.get("confidence_threshold", "N/A"), "Detection confidence threshold"]
            )
            data.append(["detector.iou_threshold", detector.get("iou_threshold", "N/A"), "NMS IOU threshold"])
            data.append(["detector.device", detector.get("device", "N/A"), "Inference device"])
            data.append(["detector.imgsz", detector.get("imgsz", "N/A"), "Inference image size"])

        # Extract tracker parameters
        if "tracker" in config:
            tracker = config["tracker"]
            data.append(["tracker.tracker_type", tracker.get("tracker_type", "N/A"), "Tracker type"])
            data.append(["tracker.track_buffer", tracker.get("track_buffer", "N/A"), "Track buffer frames"])
            data.append(["tracker.match_thresh", tracker.get("match_thresh", "N/A"), "Match threshold"])
            data.append(["tracker.track_thresh", tracker.get("track_thresh", "N/A"), "Track threshold"])
            data.append(["tracker.new_track_thresh", tracker.get("new_track_thresh", "N/A"), "New track threshold"])

        # Extract visualizer parameters
        if "visualizer" in config:
            visualizer = config["visualizer"]
            data.append(["visualizer.trajectory_length", visualizer.get("trajectory_length", "N/A"), "Trajectory display length"])
            data.append(["visualizer.line_thickness", visualizer.get("line_thickness", "N/A"), "Line thickness"])
            data.append(["visualizer.font_scale", visualizer.get("font_scale", "N/A"), "Font scale"])

    # Read ByteTrack config
    if bytetrack_config_path.exists():
        with open(bytetrack_config_path, "r", encoding="utf-8") as f:
            bytetrack_config = yaml.safe_load(f)

        data.append(["bytetrack.track_buffer", bytetrack_config.get("track_buffer", "N/A"), "ByteTrack track buffer"])
        data.append(["bytetrack.track_high_thresh", bytetrack_config.get("track_high_thresh", "N/A"), "ByteTrack high threshold"])
        data.append(["bytetrack.track_low_thresh", bytetrack_config.get("track_low_thresh", "N/A"), "ByteTrack low threshold"])
        data.append(["bytetrack.match_thresh", bytetrack_config.get("match_thresh", "N/A"), "ByteTrack match threshold"])

    # Write to CSV
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Parameter", "Default Value", "Description"])
        writer.writerows(data)

    print(f"Saved: {output_path}")


def generate_csv_field_description(output_path: Path) -> None:
    """Generate CSV field description table.

    Args:
        output_path: Path to save the CSV
    """
    data = [
        ["track_id", "Unique identifier for each tracked person"],
        ["frame_id", "Frame number in the video"],
        ["timestamp", "Time in seconds from the start of the video"],
        ["x", "X coordinate of the top-left corner of the bounding box"],
        ["y", "Y coordinate of the top-left corner of the bounding box"],
        ["w", "Width of the bounding box"],
        ["h", "Height of the bounding box"],
        ["confidence", "Detection confidence score (0.0 to 1.0)"],
        ["class_name", "Detected class name (always 'person' for this system)"],
    ]

    # Write to CSV
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Field", "Description"])
        writer.writerows(data)

    print(f"Saved: {output_path}")


def generate_experiment_video_info(video_info_csv: Path, output_path: Path) -> None:
    """Generate experiment video info table.

    Args:
        video_info_csv: Path to video info CSV
        output_path: Path to save the CSV
    """
    if not video_info_csv.exists():
        print(f"Video info CSV not found: {video_info_csv}")
        return

    # Read video info
    import pandas as pd

    df = pd.read_csv(video_info_csv)

    # Select and rename columns for thesis
    thesis_columns = {
        "video_name": "Video Name",
        "scene_type": "Scene Type",
        "resolution_width": "Width",
        "resolution_height": "Height",
        "input_fps": "FPS",
        "total_frames": "Total Frames",
        "duration_seconds": "Duration (s)",
        "file_size_mb": "File Size (MB)",
    }

    # Create new DataFrame with selected columns
    thesis_df = df[list(thesis_columns.keys())].rename(columns=thesis_columns)

    # Write to CSV
    output_path.parent.mkdir(parents=True, exist_ok=True)
    thesis_df.to_csv(output_path, index=False)

    print(f"Saved: {output_path}")


def main():
    """Main function."""
    # Define paths
    script_dir = Path(__file__).parent
    paper_assets_dir = script_dir.parent
    person_tracking_dir = paper_assets_dir.parent
    config_dir = person_tracking_dir / "config"
    tables_dir = paper_assets_dir / "tables"

    video_info_csv = paper_assets_dir / "raw" / "video_info.csv"

    print("=" * 60)
    print("Generate Paper Tables")
    print("=" * 60)
    print(f"Config directory: {config_dir}")
    print(f"Tables directory: {tables_dir}")
    print()

    # Generate tables
    print("Generating tables...")

    # 1. System environment
    generate_system_environment(tables_dir / "system_environment.csv")

    # 2. Key parameters
    generate_key_parameters(config_dir, tables_dir / "key_parameters.csv")

    # 3. CSV field description
    generate_csv_field_description(tables_dir / "csv_field_description.csv")

    # 4. Experiment video info
    generate_experiment_video_info(video_info_csv, tables_dir / "experiment_video_info.csv")

    # 5. Performance summary (already exists)
    # 6. Tracking summary (already exists)

    print()
    print("=" * 60)
    print("Done!")
    print("=" * 60)
    print(f"\nTables saved to: {tables_dir}")


if __name__ == "__main__":
    # Import psutil for RAM info
    try:
        import psutil
    except ImportError:
        psutil = None

    main()
