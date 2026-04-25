#!/usr/bin/env python
"""Generate paper figures for thesis experiments.

This script generates statistical figures for thesis, including:
1. FPS comparison
2. Processing time comparison
3. Person count over time
4. Confidence distribution
5. Trajectory example
6. Resource usage
"""

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict


def set_matplotlib_style():
    """Set matplotlib style for thesis figures."""
    plt.style.use("default")
    plt.rcParams["font.family"] = "serif"
    plt.rcParams["font.serif"] = ["Times New Roman"]
    plt.rcParams["font.size"] = 12
    plt.rcParams["axes.labelsize"] = 12
    plt.rcParams["axes.titlesize"] = 14
    plt.rcParams["xtick.labelsize"] = 10
    plt.rcParams["ytick.labelsize"] = 10
    plt.rcParams["legend.fontsize"] = 10
    plt.rcParams["figure.dpi"] = 300


def plot_fps_comparison(performance_csv: Path, output_path: Path) -> None:
    """Plot FPS comparison for different scenes.

    Args:
        performance_csv: Path to performance summary CSV
        output_path: Path to save the figure
    """
    df = pd.read_csv(performance_csv)

    # Create bar chart
    fig, ax = plt.subplots(figsize=(8, 6))

    scenes = df["video_name"].tolist()
    fps_values = df["avg_fps"].tolist()

    bars = ax.bar(scenes, fps_values, color="steelblue", alpha=0.7)

    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            height,
            f"{height:.1f}",
            ha="center",
            va="bottom",
        )

    ax.set_xlabel("Test Scene")
    ax.set_ylabel("Average FPS")
    ax.set_title("Average FPS Comparison Across Test Scenes")
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"Saved: {output_path}")


def plot_processing_time_comparison(
    performance_csv: Path,
    output_path: Path,
) -> None:
    """Plot processing time comparison for different scenes.

    Args:
        performance_csv: Path to performance summary CSV
        output_path: Path to save the figure
    """
    df = pd.read_csv(performance_csv)

    # Create bar chart
    fig, ax = plt.subplots(figsize=(8, 6))

    scenes = df["video_name"].tolist()
    processing_times = df["avg_processing_time_ms"].tolist()

    bars = ax.bar(scenes, processing_times, color="coral", alpha=0.7)

    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            height,
            f"{height:.1f}",
            ha="center",
            va="bottom",
        )

    ax.set_xlabel("Test Scene")
    ax.set_ylabel("Average Processing Time (ms)")
    ax.set_title("Average Processing Time Comparison Across Test Scenes")
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"Saved: {output_path}")


def plot_person_count_over_time(
    csv_path: Path,
    output_path: Path,
) -> None:
    """Plot person count over time for multi-person scene.

    Args:
        csv_path: Path to multi-person tracking CSV
        output_path: Path to save the figure
    """
    df = pd.read_csv(csv_path)

    # Count persons per frame
    frame_counts = df.groupby("frame_id").size()

    # Create line plot
    fig, ax = plt.subplots(figsize=(10, 6))

    ax.plot(
        frame_counts.index,
        frame_counts.values,
        color="darkblue",
        linewidth=1.5,
        alpha=0.8,
    )

    ax.set_xlabel("Frame Index")
    ax.set_ylabel("Number of Detected Persons")
    ax.set_title("Person Count Over Time in Multi-Person Scene")
    ax.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"Saved: {output_path}")


def plot_confidence_distribution(
    csv_dir: Path,
    output_path: Path,
) -> None:
    """Plot confidence distribution across all videos.

    Args:
        csv_dir: Directory containing CSV files
        output_path: Path to save the figure
    """
    # Collect all confidence values
    all_confidences = []

    for csv_file in csv_dir.glob("*_tracks.csv"):
        df = pd.read_csv(csv_file)
        all_confidences.extend(df["confidence"].tolist())

    # Create histogram
    fig, ax = plt.subplots(figsize=(8, 6))

    ax.hist(
        all_confidences,
        bins=30,
        color="mediumseagreen",
        alpha=0.7,
        edgecolor="black",
    )

    ax.set_xlabel("Detection Confidence")
    ax.set_ylabel("Frequency")
    ax.set_title("Detection Confidence Distribution")
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"Saved: {output_path}")


def plot_trajectory_example(
    csv_path: Path,
    output_path: Path,
) -> None:
    """Plot trajectory example for a single track.

    Args:
        csv_path: Path to tracking CSV
        output_path: Path to save the figure
    """
    df = pd.read_csv(csv_path)

    # Select the track with the most points
    track_counts = df.groupby("track_id").size()
    longest_track_id = track_counts.idxmax()

    # Get trajectory for this track
    track_data = df[df["track_id"] == longest_track_id].sort_values("frame_id")

    # Calculate center points
    track_data["center_x"] = track_data["x"] + track_data["w"] / 2
    track_data["center_y"] = track_data["y"] + track_data["h"] / 2

    # Create scatter plot
    fig, ax = plt.subplots(figsize=(8, 6))

    # Plot trajectory with color gradient based on frame index
    scatter = ax.scatter(
        track_data["center_x"],
        track_data["center_y"],
        c=track_data["frame_id"],
        cmap="viridis",
        s=20,
        alpha=0.7,
    )

    # Add colorbar
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label("Frame Index")

    # Mark start and end points
    ax.scatter(
        track_data.iloc[0]["center_x"],
        track_data.iloc[0]["center_y"],
        color="green",
        s=100,
        marker="o",
        label="Start",
    )
    ax.scatter(
        track_data.iloc[-1]["center_x"],
        track_data.iloc[-1]["center_y"],
        color="red",
        s=100,
        marker="s",
        label="End",
    )

    ax.set_xlabel("X Position (pixels)")
    ax.set_ylabel("Y Position (pixels)")
    ax.set_title(f"Trajectory Example (Track ID: {longest_track_id})")
    ax.legend()
    ax.grid(alpha=0.3)
    ax.set_aspect("equal", adjustable="box")

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"Saved: {output_path}")


def plot_resource_usage(
    performance_csv: Path,
    output_path: Path,
) -> None:
    """Plot resource usage over time (simplified version).

    Note: This is a simplified version since we don't have frame-by-frame resource data.
    We'll show average resource usage per scene.

    Args:
        performance_csv: Path to performance summary CSV
        output_path: Path to save the figure
    """
    df = pd.read_csv(performance_csv)

    # Create bar chart for average FPS (as proxy for resource usage)
    fig, ax = plt.subplots(figsize=(8, 6))

    scenes = df["video_name"].tolist()
    fps_values = df["avg_fps"].tolist()

    bars = ax.bar(scenes, fps_values, color="orchid", alpha=0.7)

    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            height,
            f"{height:.1f}",
            ha="center",
            va="bottom",
        )

    ax.set_xlabel("Test Scene")
    ax.set_ylabel("Average FPS (Resource Usage Indicator)")
    ax.set_title("System Resource Usage Across Test Scenes")
    ax.grid(axis="y", alpha=0.3)

    # Add note
    ax.text(
        0.5,
        -0.15,
        "Note: Higher FPS indicates better resource utilization",
        ha="center",
        va="center",
        transform=ax.transAxes,
        fontsize=9,
        style="italic",
    )

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"Saved: {output_path}")


def main():
    """Main function."""
    # Set matplotlib style
    set_matplotlib_style()

    # Define paths
    script_dir = Path(__file__).parent
    paper_assets_dir = script_dir.parent
    csv_dir = paper_assets_dir / "raw" / "csv"
    performance_csv = paper_assets_dir / "tables" / "performance_summary.csv"
    figures_dir = paper_assets_dir / "figures" / "chapter5"

    figures_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Generate Paper Figures")
    print("=" * 60)
    print(f"CSV directory: {csv_dir}")
    print(f"Performance CSV: {performance_csv}")
    print(f"Figures directory: {figures_dir}")
    print()

    # Generate figures
    print("Generating figures...")

    # 1. FPS comparison
    plot_fps_comparison(
        performance_csv,
        figures_dir / "fps_comparison.png",
    )

    # 2. Processing time comparison
    plot_processing_time_comparison(
        performance_csv,
        figures_dir / "processing_time_comparison.png",
    )

    # 3. Person count over time (multi-person)
    multi_person_csv = csv_dir / "multi_person_tracks.csv"
    if multi_person_csv.exists():
        plot_person_count_over_time(
            multi_person_csv,
            figures_dir / "person_count_over_time_multi.png",
        )

    # 4. Confidence distribution
    plot_confidence_distribution(
        csv_dir,
        figures_dir / "confidence_distribution.png",
    )

    # 5. Trajectory example (use multi-person)
    if multi_person_csv.exists():
        plot_trajectory_example(
            multi_person_csv,
            figures_dir / "trajectory_example.png",
        )

    # 6. Resource usage
    plot_resource_usage(
        performance_csv,
        figures_dir / "resource_usage.png",
    )

    print()
    print("=" * 60)
    print("Done!")
    print("=" * 60)
    print(f"\nFigures saved to: {figures_dir}")


if __name__ == "__main__":
    main()
