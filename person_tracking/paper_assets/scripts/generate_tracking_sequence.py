#!/usr/bin/env python
"""Generate a tracking sequence figure from multi-person results.

This script selects 3 to 4 consecutive frames from the annotated tracking video,
labels them as Frame 1..N, and stitches them into a single horizontal image.
It prefers frame windows with the highest person counts based on the tracking CSV.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

import cv2
import numpy as np
import pandas as pd


def read_frame_counts(csv_path: Path, total_frames: int) -> np.ndarray:
    """Read per-frame person counts from tracking CSV.

    Args:
        csv_path: Path to *_tracks.csv
        total_frames: Total frame count in the video

    Returns:
        Array of length total_frames with counts per frame.
    """
    counts = np.zeros(total_frames, dtype=int)
    if not csv_path.exists():
        return counts

    df = pd.read_csv(csv_path)
    if df.empty or "frame_id" not in df.columns:
        return counts

    grouped = df.groupby("frame_id").size()
    for frame_id, count in grouped.items():
        if 0 <= int(frame_id) < total_frames:
            counts[int(frame_id)] = int(count)

    return counts


def select_best_window(counts: np.ndarray, window_size: int) -> int:
    """Select the start index for the best consecutive frame window.

    The best window is the one with the highest total person count.
    """
    if len(counts) <= window_size:
        return 0

    window = np.ones(window_size, dtype=int)
    sums = np.convolve(counts, window, mode="valid")
    return int(np.argmax(sums))


def extract_frames(video_path: Path, frame_indices: List[int]) -> List[np.ndarray]:
    """Extract frames by index from a video."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    frames: List[np.ndarray] = []
    for frame_idx in frame_indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if not ret:
            raise RuntimeError(f"Failed to read frame {frame_idx}")
        frames.append(frame)

    cap.release()
    return frames


def add_frame_label(frame: np.ndarray, label: str) -> np.ndarray:
    """Add a label in the top-left corner of a frame."""
    labeled = frame.copy()
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 2.6
    thickness = 6
    padding = 24

    text_size, baseline = cv2.getTextSize(label, font, font_scale, thickness)
    text_w, text_h = text_size

    x0, y0 = 10, 10
    x1 = x0 + text_w + padding * 2
    y1 = y0 + text_h + padding * 2

    cv2.rectangle(labeled, (x0, y0), (x1, y1), (255, 255, 255), -1)
    cv2.putText(
        labeled,
        label,
        (x0 + padding, y0 + text_h + padding - baseline),
        font,
        font_scale,
        (0, 0, 0),
        thickness,
        cv2.LINE_AA,
    )
    return labeled


def resize_frames(
    frames: List[np.ndarray],
    target_width: int,
    target_height: int | None = None,
) -> List[np.ndarray]:
    """Resize frames to a uniform size while keeping aspect ratio."""
    if target_width <= 0:
        return frames

    resized = []
    base_h = None
    if target_height is None and frames:
        h, w = frames[0].shape[:2]
        scale = target_width / float(w)
        base_h = int(h * scale)
    else:
        base_h = target_height

    for frame in frames:
        h, w = frame.shape[:2]
        scale = target_width / float(w)
        new_h = int(h * scale) if base_h is None else base_h
        resized.append(cv2.resize(frame, (target_width, new_h)))
    return resized


def stitch_frames_grid(frames: List[np.ndarray], rows: int, cols: int) -> np.ndarray:
    """Stitch frames into a grid image."""
    if not frames:
        raise ValueError("No frames to stitch")
    if len(frames) != rows * cols:
        raise ValueError("Frame count does not match grid size")

    grid_rows = []
    for r in range(rows):
        row_frames = frames[r * cols:(r + 1) * cols]
        grid_rows.append(np.hstack(row_frames))
    return np.vstack(grid_rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a multi-frame tracking sequence image.",
    )
    parser.add_argument(
        "--video",
        type=Path,
        default=Path(__file__).parent.parent
        / "processed"
        / "tracking_results"
        / "multi_person_tracked.mp4",
        help="Annotated tracking video path",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=Path(__file__).parent.parent / "raw" / "csv" / "multi_person_tracks.csv",
        help="Tracking CSV path used to pick dense frames",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent.parent
        / "figures"
        / "chapter5"
        / "tracking_sequence.png",
        help="Output image path",
    )
    parser.add_argument(
        "--num-frames",
        type=int,
        default=4,
        help="Number of consecutive frames to stitch (must be 4 for 2x2)",
    )
    parser.add_argument(
        "--target-width",
        type=int,
        default=640,
        help="Resize each frame to this width before stitching",
    )
    parser.add_argument(
        "--start-frame",
        type=int,
        default=None,
        help="Optional start frame override (0-based)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.num_frames != 4:
        raise ValueError("--num-frames must be 4 for a 2x2 grid")

    if not args.video.exists():
        raise FileNotFoundError(f"Video not found: {args.video}")

    cap = cv2.VideoCapture(str(args.video))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {args.video}")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()

    if total_frames < 3:
        raise RuntimeError(f"Video too short: {total_frames} frames")

    num_frames = min(args.num_frames, total_frames)

    if args.start_frame is not None:
        start_frame = max(0, min(args.start_frame, total_frames - num_frames))
    else:
        counts = read_frame_counts(args.csv, total_frames)
        start_frame = select_best_window(counts, num_frames)

    frame_indices = list(range(start_frame, start_frame + num_frames))

    frames = extract_frames(args.video, frame_indices)
    labeled_frames = [
        add_frame_label(frame, f"Frame {i + 1}")
        for i, frame in enumerate(frames)
    ]

    resized_frames = resize_frames(labeled_frames, args.target_width)
    sequence = stitch_frames_grid(resized_frames, rows=2, cols=2)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(args.output), sequence)

    print("Selected frame indices:", frame_indices)
    print(f"Saved tracking sequence: {args.output}")


if __name__ == "__main__":
    main()
