#!/usr/bin/env python
"""Analyze tracking results for thesis experiments.

This script analyzes tracking results from CSV files, including:
- Detection statistics
- Tracking statistics
- Confidence distribution
- Track length distribution
- Possible ID switches (heuristic estimation)
"""

import csv
from pathlib import Path
from typing import List, Dict, Tuple
import pandas as pd
import numpy as np


def detect_possible_id_switches(df: pd.DataFrame) -> int:
    """Detect possible ID switches using heuristic rules.

    Rules:
    1. Same target disappears and reappears with different ID in nearby frames
    2. Short time gap between disappearance and reappearance
    3. Spatial proximity

    Args:
        df: DataFrame with tracking results

    Returns:
        Number of possible ID switches
    """
    if df.empty:
        return 0

    # Group by track_id
    track_groups = df.groupby("track_id")

    # For each track, find its first and last frame
    track_ranges = []
    for track_id, group in track_groups:
        first_frame = group["frame_id"].min()
        last_frame = group["frame_id"].max()
        track_ranges.append((track_id, first_frame, last_frame))

    # Sort by first frame
    track_ranges.sort(key=lambda x: x[1])

    # Detect possible ID switches
    possible_switches = 0

    for i in range(len(track_ranges) - 1):
        track_id1, first1, last1 = track_ranges[i]
        track_id2, first2, last2 = track_ranges[i + 1]

        # Check if track2 starts shortly after track1 ends
        gap = first2 - last1

        # If gap is small (e.g., < 10 frames), it might be an ID switch
        if 0 < gap < 10:
            # Check spatial proximity
            # Get last position of track1 and first position of track2
            track1_last = df[(df["track_id"] == track_id1) & (df["frame_id"] == last1)]
            track2_first = df[(df["track_id"] == track_id2) & (df["frame_id"] == first2)]

            if not track1_last.empty and not track2_first.empty:
                # Calculate center points
                x1, y1 = track1_last.iloc[0]["x"] + track1_last.iloc[0]["w"] / 2, track1_last.iloc[0]["y"] + track1_last.iloc[0]["h"] / 2
                x2, y2 = track2_first.iloc[0]["x"] + track2_first.iloc[0]["w"] / 2, track2_first.iloc[0]["y"] + track2_first.iloc[0]["h"] / 2

                # Calculate distance
                distance = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

                # If distance is small (e.g., < 100 pixels), it might be an ID switch
                if distance < 100:
                    possible_switches += 1

    return possible_switches


def analyze_tracking_results(csv_path: Path) -> Dict[str, any]:
    """Analyze tracking results from CSV file.

    Args:
        csv_path: Path to CSV file

    Returns:
        Dictionary containing analysis results
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

        # Bounding box statistics
        df["bbox_area"] = df["w"] * df["h"]
        avg_bbox_area = df["bbox_area"].mean()

        # Frame statistics
        frame_counts = df.groupby("frame_id").size()
        avg_person_count = frame_counts.mean()
        max_person_count = frame_counts.max()

        # Track length statistics
        track_lengths = df.groupby("track_id").size()
        avg_track_length = track_lengths.mean()
        max_track_length = track_lengths.max()
        min_track_length = track_lengths.min()

        # Detect possible ID switches
        possible_id_switches = detect_possible_id_switches(df)

        return {
            "total_detections": total_detections,
            "total_unique_tracks": unique_tracks,
            "avg_confidence": avg_confidence,
            "min_confidence": min_confidence,
            "max_confidence": max_confidence,
            "avg_bbox_area": avg_bbox_area,
            "avg_person_count_per_frame": avg_person_count,
            "max_person_count_per_frame": max_person_count,
            "track_length_avg_frames": avg_track_length,
            "track_length_max_frames": max_track_length,
            "track_length_min_frames": min_track_length,
            "possible_id_switch_count": possible_id_switches,
        }

    except Exception as e:
        print(f"Error analyzing tracking results: {e}")
        return {}


def analyze_all_tracking_results(
    csv_dir: Path,
    output_csv: Path,
    output_report: Path,
) -> None:
    """Analyze tracking results for all videos.

    Args:
        csv_dir: Directory containing CSV files
        output_csv: Path to output CSV file
        output_report: Path to output report file
    """
    # Find all CSV files
    csv_files = list(csv_dir.glob("*_tracks.csv"))

    if not csv_files:
        print(f"No CSV files found in {csv_dir}")
        return

    # Analyze tracking results for each video
    tracking_results = []

    for csv_file in sorted(csv_files):
        video_name = csv_file.stem.replace("_tracks", "")
        print(f"Analyzing: {video_name}")

        # Analyze tracking results
        results = analyze_tracking_results(csv_file)
        results["video_name"] = video_name
        results["scene_type"] = video_name

        tracking_results.append(results)

        print(f"  - Total detections: {results.get('total_detections', 'N/A')}")
        print(f"  - Unique tracks: {results.get('total_unique_tracks', 'N/A')}")
        print(f"  - Avg confidence: {results.get('avg_confidence', 'N/A'):.4f}")
        print(f"  - Possible ID switches: {results.get('possible_id_switch_count', 'N/A')}")

    # Write to CSV
    if tracking_results:
        output_csv.parent.mkdir(parents=True, exist_ok=True)

        # Get all field names
        fieldnames = set()
        for data in tracking_results:
            fieldnames.update(data.keys())
        fieldnames = sorted(fieldnames)

        with open(output_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(tracking_results)

        print(f"\nTracking results saved to: {output_csv}")
        print(f"Total videos analyzed: {len(tracking_results)}")

        # Generate report
        generate_tracking_report(tracking_results, output_report)
    else:
        print("No tracking results collected")


def generate_tracking_report(tracking_results: List[Dict], output_report: Path) -> None:
    """Generate tracking analysis report.

    Args:
        tracking_results: List of tracking result dictionaries
        output_report: Path to output report file
    """
    output_report.parent.mkdir(parents=True, exist_ok=True)

    with open(output_report, "w", encoding="utf-8") as f:
        f.write("# Tracking Analysis Report\n\n")
        f.write("## Overview\n\n")
        f.write(f"Total videos analyzed: {len(tracking_results)}\n\n")

        f.write("## Detailed Results\n\n")

        for results in tracking_results:
            video_name = results.get("video_name", "Unknown")
            f.write(f"### {video_name}\n\n")

            f.write("#### Detection Statistics\n")
            f.write(f"- Total detections: {results.get('total_detections', 'N/A')}\n")
            f.write(f"- Unique tracks: {results.get('total_unique_tracks', 'N/A')}\n")
            f.write(f"- Average confidence: {results.get('avg_confidence', 'N/A'):.4f}\n")
            f.write(f"- Min confidence: {results.get('min_confidence', 'N/A'):.4f}\n")
            f.write(f"- Max confidence: {results.get('max_confidence', 'N/A'):.4f}\n")
            f.write(f"- Average bbox area: {results.get('avg_bbox_area', 'N/A'):.2f}\n")
            f.write("\n")

            f.write("#### Frame Statistics\n")
            f.write(f"- Average person count per frame: {results.get('avg_person_count_per_frame', 'N/A'):.2f}\n")
            f.write(f"- Max person count per frame: {results.get('max_person_count_per_frame', 'N/A')}\n")
            f.write("\n")

            f.write("#### Track Statistics\n")
            f.write(f"- Average track length: {results.get('track_length_avg_frames', 'N/A'):.2f} frames\n")
            f.write(f"- Max track length: {results.get('track_length_max_frames', 'N/A')} frames\n")
            f.write(f"- Min track length: {results.get('track_length_min_frames', 'N/A')} frames\n")
            f.write("\n")

            f.write("#### ID Switch Detection\n")
            f.write(f"- Possible ID switches: {results.get('possible_id_switch_count', 'N/A')}\n")
            f.write("\n")
            f.write("**Note**: ID switch detection uses heuristic rules and is not equivalent to standard MOT metrics.\n")
            f.write("\n")

        f.write("## Summary\n\n")
        f.write("All tracking results have been analyzed and saved to CSV format.\n")
        f.write("The analysis includes detection statistics, tracking statistics, and heuristic ID switch detection.\n")
        f.write("\n")
        f.write("## Notes\n\n")
        f.write("1. ID switch detection is based on heuristic rules and may not be accurate.\n")
        f.write("2. For standard MOT metrics (Precision, Recall, mAP, MOTA, IDF1), ground truth annotations are required.\n")
        f.write("3. The current analysis provides statistics that can be directly derived from the tracking results.\n")


def main():
    """Main function."""
    # Define paths
    script_dir = Path(__file__).parent
    paper_assets_dir = script_dir.parent
    csv_dir = paper_assets_dir / "raw" / "csv"
    output_csv = paper_assets_dir / "tables" / "tracking_summary.csv"
    output_report = paper_assets_dir / "reports" / "tracking_analysis_report.md"

    print("=" * 60)
    print("Tracking Results Analysis")
    print("=" * 60)
    print(f"CSV directory: {csv_dir}")
    print(f"Output CSV: {output_csv}")
    print(f"Output report: {output_report}")
    print()

    # Analyze tracking results
    analyze_all_tracking_results(csv_dir, output_csv, output_report)

    print()
    print("=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()
