#!/usr/bin/env python
"""Collect performance data from tracking results.

This script collects performance metrics from CSV files and logs,
including FPS, processing time, detection counts, and resource usage.
"""

import csv
import re
from pathlib import Path
from typing import List, Dict
import pandas as pd


def extract_performance_from_log(log_path: Path) -> Dict[str, any]:
    """Extract performance data from log file.

    Args:
        log_path: Path to log file

    Returns:
        Dictionary containing performance data
    """
    if not log_path.exists():
        return {}

    performance_data = {}

    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            # Look for "Processing completed" line
            if "Processing completed:" in line:
                # Extract: 300 frames, 29.95s, 10.0 FPS
                match = re.search(
                    r"Processing completed: (\d+) frames, ([\d.]+)s, ([\d.]+) FPS",
                    line,
                )
                if match:
                    performance_data["total_frames"] = int(match.group(1))
                    performance_data["elapsed_time"] = float(match.group(2))
                    performance_data["avg_fps"] = float(match.group(3))

            # Look for "CSVExporter closed" line
            if "CSVExporter closed:" in line:
                # Extract: 279 rows written
                match = re.search(r"CSVExporter closed: (\d+) rows written", line)
                if match:
                    performance_data["total_detections"] = int(match.group(1))

    return performance_data


def analyze_csv_performance(csv_path: Path) -> Dict[str, any]:
    """Analyze performance from CSV file.

    Args:
        csv_path: Path to CSV file

    Returns:
        Dictionary containing performance analysis
    """
    if not csv_path.exists():
        return {}

    try:
        df = pd.read_csv(csv_path)

        if df.empty:
            return {}

        # Basic statistics
        total_detections = len(df)
        unique_tracks = df["track_id"].nunique()
        avg_confidence = df["confidence"].mean()
        min_confidence = df["confidence"].min()
        max_confidence = df["confidence"].max()

        # Frame statistics
        frame_counts = df.groupby("frame_id").size()
        avg_person_count = frame_counts.mean()
        max_person_count = frame_counts.max()

        # Track length statistics
        track_lengths = df.groupby("track_id").size()
        avg_track_length = track_lengths.mean()
        max_track_length = track_lengths.max()
        min_track_length = track_lengths.min()

        return {
            "total_detections": total_detections,
            "total_unique_tracks": unique_tracks,
            "avg_confidence": avg_confidence,
            "min_confidence": min_confidence,
            "max_confidence": max_confidence,
            "avg_person_count_per_frame": avg_person_count,
            "max_person_count_per_frame": max_person_count,
            "track_length_avg_frames": avg_track_length,
            "track_length_max_frames": max_track_length,
            "track_length_min_frames": min_track_length,
        }

    except Exception as e:
        print(f"Error analyzing CSV: {e}")
        return {}


def collect_all_performance_data(
    csv_dir: Path,
    log_dir: Path,
    output_csv: Path,
) -> None:
    """Collect performance data for all videos.

    Args:
        csv_dir: Directory containing CSV files
        log_dir: Directory containing log files
        output_csv: Path to output CSV file
    """
    # Find all CSV files
    csv_files = list(csv_dir.glob("*_tracks.csv"))

    if not csv_files:
        print(f"No CSV files found in {csv_dir}")
        return

    # Collect performance data for each video
    performance_list = []

    for csv_file in sorted(csv_files):
        video_name = csv_file.stem.replace("_tracks", "")
        print(f"Processing: {video_name}")

        # Analyze CSV
        csv_performance = analyze_csv_performance(csv_file)

        # Extract from log (if available)
        log_file = log_dir / f"{video_name}_run.log"
        log_performance = extract_performance_from_log(log_file)

        # Combine data
        performance_data = {
            "video_name": video_name,
            "scene_type": video_name,
            **csv_performance,
            **log_performance,
        }

        # Calculate derived metrics
        if "total_frames" in performance_data and "elapsed_time" in performance_data:
            if performance_data["elapsed_time"] > 0:
                performance_data["avg_processing_time_ms"] = (
                    performance_data["elapsed_time"] * 1000
                    / performance_data["total_frames"]
                )

        performance_list.append(performance_data)

        print(f"  - Total detections: {performance_data.get('total_detections', 'N/A')}")
        print(f"  - Unique tracks: {performance_data.get('total_unique_tracks', 'N/A')}")
        print(f"  - Avg FPS: {performance_data.get('avg_fps', 'N/A')}")

    # Write to CSV
    if performance_list:
        output_csv.parent.mkdir(parents=True, exist_ok=True)

        # Get all field names
        fieldnames = set()
        for data in performance_list:
            fieldnames.update(data.keys())
        fieldnames = sorted(fieldnames)

        with open(output_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(performance_list)

        print(f"\nPerformance data saved to: {output_csv}")
        print(f"Total videos processed: {len(performance_list)}")
    else:
        print("No performance data collected")


def main():
    """Main function."""
    # Define paths
    script_dir = Path(__file__).parent
    paper_assets_dir = script_dir.parent
    csv_dir = paper_assets_dir / "raw" / "csv"
    log_dir = paper_assets_dir / "raw" / "logs"
    output_csv = paper_assets_dir / "tables" / "performance_summary.csv"

    print("=" * 60)
    print("Performance Data Collection")
    print("=" * 60)
    print(f"CSV directory: {csv_dir}")
    print(f"Log directory: {log_dir}")
    print(f"Output CSV: {output_csv}")
    print()

    # Collect performance data
    collect_all_performance_data(csv_dir, log_dir, output_csv)

    print()
    print("=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()
