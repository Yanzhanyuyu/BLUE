#!/usr/bin/env python
"""Collect video information for thesis experiments.

This script collects basic information about test videos including:
- video_name
- scene_type
- source_path
- resolution_width
- resolution_height
- input_fps
- total_frames
- duration_seconds
- codec
- file_size_mb
"""

import csv
import os
from pathlib import Path
from typing import List, Dict
import cv2


def get_video_info(video_path: Path) -> Dict[str, any]:
    """Get video information using OpenCV.

    Args:
        video_path: Path to video file

    Returns:
        Dictionary containing video information
    """
    cap = cv2.VideoCapture(str(video_path))

    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {video_path}")

    # Get video properties
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Get codec
    fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
    codec = "".join([chr((fourcc >> 8 * i) & 0xFF) for i in range(4)])

    # Calculate duration
    if fps > 0:
        duration_seconds = total_frames / fps
    else:
        duration_seconds = 0.0

    # Get file size
    file_size_mb = video_path.stat().st_size / (1024 * 1024)

    cap.release()

    return {
        "video_name": video_path.name,
        "scene_type": video_path.stem,
        "source_path": str(video_path),
        "resolution_width": width,
        "resolution_height": height,
        "input_fps": fps,
        "total_frames": total_frames,
        "duration_seconds": duration_seconds,
        "codec": codec,
        "file_size_mb": round(file_size_mb, 2),
    }


def collect_all_videos(
    input_dir: Path,
    output_csv: Path,
) -> None:
    """Collect information for all videos in input directory.

    Args:
        input_dir: Directory containing video files
        output_csv: Path to output CSV file
    """
    # Find all video files
    video_extensions = [".mp4", ".avi", ".mov", ".mkv"]
    video_files = []

    for ext in video_extensions:
        video_files.extend(input_dir.glob(f"*{ext}"))

    if not video_files:
        print(f"No video files found in {input_dir}")
        return

    # Collect information for each video
    video_info_list = []
    for video_file in sorted(video_files):
        print(f"Processing: {video_file.name}")
        try:
            info = get_video_info(video_file)
            video_info_list.append(info)
            print(f"  - Resolution: {info['resolution_width']}x{info['resolution_height']}")
            print(f"  - FPS: {info['input_fps']:.2f}")
            print(f"  - Frames: {info['total_frames']}")
            print(f"  - Duration: {info['duration_seconds']:.2f}s")
        except Exception as e:
            print(f"  - Error: {e}")

    # Write to CSV
    if video_info_list:
        output_csv.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = [
            "video_name",
            "scene_type",
            "source_path",
            "resolution_width",
            "resolution_height",
            "input_fps",
            "total_frames",
            "duration_seconds",
            "codec",
            "file_size_mb",
        ]

        with open(output_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(video_info_list)

        print(f"\nVideo information saved to: {output_csv}")
        print(f"Total videos processed: {len(video_info_list)}")
    else:
        print("No video information collected")


def main():
    """Main function."""
    # Define paths
    # The script is in: person_tracking/paper_assets/scripts/
    # Project root is: BLUE/
    # Input dir is: BLUE/input/
    # Output CSV is: BLUE/person_tracking/paper_assets/raw/video_info.csv
    script_dir = Path(__file__).parent
    paper_assets_dir = script_dir.parent
    person_tracking_dir = paper_assets_dir.parent
    project_root = person_tracking_dir.parent

    input_dir = project_root / "input"
    output_csv = paper_assets_dir / "raw" / "video_info.csv"

    print("=" * 60)
    print("Video Information Collection")
    print("=" * 60)
    print(f"Input directory: {input_dir}")
    print(f"Output CSV: {output_csv}")
    print()

    # Collect video information
    collect_all_videos(input_dir, output_csv)

    print()
    print("=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()
