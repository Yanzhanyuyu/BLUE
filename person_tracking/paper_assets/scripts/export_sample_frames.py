#!/usr/bin/env python
"""Export sample frames for thesis experiments.

This script exports key frames from tracking result videos for thesis figures.
"""

import cv2
import numpy as np
from pathlib import Path
from typing import List, Tuple


def extract_frames_from_video(
    video_path: Path,
    output_dir: Path,
    frame_indices: List[int],
    prefix: str,
) -> None:
    """Extract frames from video at specified indices.

    Args:
        video_path: Path to video file
        output_dir: Directory to save extracted frames
        frame_indices: List of frame indices to extract
        prefix: Prefix for output filenames
    """
    if not video_path.exists():
        print(f"Video not found: {video_path}")
        return

    cap = cv2.VideoCapture(str(video_path))

    if not cap.isOpened():
        print(f"Cannot open video: {video_path}")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    for i, frame_idx in enumerate(frame_indices):
        if frame_idx >= total_frames:
            print(f"Frame index {frame_idx} exceeds total frames {total_frames}")
            continue

        # Set frame position
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)

        # Read frame
        ret, frame = cap.read()

        if not ret:
            print(f"Failed to read frame {frame_idx}")
            continue

        # Save frame
        output_path = output_dir / f"{prefix}_{i+1}.png"
        cv2.imwrite(str(output_path), frame)
        print(f"Saved: {output_path}")

    cap.release()


def create_frame_sequence(
    video_path: Path,
    output_path: Path,
    frame_indices: List[int],
    layout: str = "horizontal",
) -> None:
    """Create a sequence of frames as a single image.

    Args:
        video_path: Path to video file
        output_path: Path to save the sequence image
        frame_indices: List of frame indices to include
        layout: Layout of the sequence ('horizontal' or 'vertical')
    """
    if not video_path.exists():
        print(f"Video not found: {video_path}")
        return

    cap = cv2.VideoCapture(str(video_path))

    if not cap.isOpened():
        print(f"Cannot open video: {video_path}")
        return

    frames = []
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    for frame_idx in frame_indices:
        if frame_idx >= total_frames:
            print(f"Frame index {frame_idx} exceeds total frames {total_frames}")
            continue

        # Set frame position
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)

        # Read frame
        ret, frame = cap.read()

        if not ret:
            print(f"Failed to read frame {frame_idx}")
            continue

        frames.append(frame)

    cap.release()

    if not frames:
        print("No frames extracted")
        return

    # Create sequence image
    if layout == "horizontal":
        # Resize all frames to the same height
        target_height = frames[0].shape[0]
        resized_frames = []
        for frame in frames:
            h, w = frame.shape[:2]
            scale = target_height / h
            new_w = int(w * scale)
            resized = cv2.resize(frame, (new_w, target_height))
            resized_frames.append(resized)

        # Concatenate horizontally
        sequence = np.hstack(resized_frames)
    else:  # vertical
        # Resize all frames to the same width
        target_width = frames[0].shape[1]
        resized_frames = []
        for frame in frames:
            h, w = frame.shape[:2]
            scale = target_width / w
            new_h = int(h * scale)
            resized = cv2.resize(frame, (target_width, new_h))
            resized_frames.append(resized)

        # Concatenate vertically
        sequence = np.vstack(resized_frames)

    # Save sequence
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), sequence)
    print(f"Saved sequence: {output_path}")


def export_single_person_frames(
    video_path: Path,
    output_dir: Path,
) -> None:
    """Export frames for single person experiment.

    Args:
        video_path: Path to video file
        output_dir: Directory to save frames
    """
    print(f"Exporting single person frames from: {video_path}")

    # Extract key frames (beginning, middle, end)
    cap = cv2.VideoCapture(str(video_path))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()

    frame_indices = [
        int(total_frames * 0.1),  # 10% - early frame
        int(total_frames * 0.5),  # 50% - middle frame
        int(total_frames * 0.9),  # 90% - late frame
    ]

    extract_frames_from_video(
        video_path,
        output_dir,
        frame_indices,
        "single_person",
    )


def export_multi_person_frames(
    video_path: Path,
    output_dir: Path,
) -> None:
    """Export frames for multi person experiment.

    Args:
        video_path: Path to video file
        output_dir: Directory to save frames
    """
    print(f"Exporting multi person frames from: {video_path}")

    # Extract key frames
    cap = cv2.VideoCapture(str(video_path))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()

    # Single frames
    frame_indices = [
        int(total_frames * 0.25),  # 25% - multi person detection
        int(total_frames * 0.5),   # 50% - stable tracking
    ]

    extract_frames_from_video(
        video_path,
        output_dir,
        frame_indices,
        "multi_person",
    )

    # Create sequence of 3 consecutive frames
    sequence_start = int(total_frames * 0.4)
    sequence_indices = [sequence_start, sequence_start + 10, sequence_start + 20]

    create_frame_sequence(
        video_path,
        output_dir / "multi_person_tracking_sequence.png",
        sequence_indices,
        layout="horizontal",
    )


def export_occlusion_frames(
    video_path: Path,
    output_dir: Path,
) -> None:
    """Export frames for occlusion experiment.

    Args:
        video_path: Path to video file
        output_dir: Directory to save frames
    """
    print(f"Exporting occlusion frames from: {video_path}")

    # Extract key frames (before, during, after occlusion)
    cap = cv2.VideoCapture(str(video_path))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()

    frame_indices = [
        int(total_frames * 0.2),  # 20% - before occlusion
        int(total_frames * 0.5),  # 50% - during occlusion
        int(total_frames * 0.8),  # 80% - after occlusion
    ]

    extract_frames_from_video(
        video_path,
        output_dir,
        frame_indices,
        "occlusion",
    )


def main():
    """Main function."""
    # Define paths
    script_dir = Path(__file__).parent
    paper_assets_dir = script_dir.parent
    tracking_results_dir = paper_assets_dir / "processed" / "tracking_results"
    frames_output_dir = paper_assets_dir / "processed" / "frames"

    print("=" * 60)
    print("Export Sample Frames for Thesis")
    print("=" * 60)
    print(f"Tracking results directory: {tracking_results_dir}")
    print(f"Frames output directory: {frames_output_dir}")
    print()

    # Export frames for each video
    videos = {
        "single_person": export_single_person_frames,
        "multi_person": export_multi_person_frames,
        "occlusion": export_occlusion_frames,
    }

    for video_name, export_func in videos.items():
        video_path = tracking_results_dir / f"{video_name}_tracked.mp4"
        if video_path.exists():
            export_func(video_path, frames_output_dir)
            print()
        else:
            print(f"Video not found: {video_path}")
            print()

    print("=" * 60)
    print("Done!")
    print("=" * 60)
    print(f"\nFrames exported to: {frames_output_dir}")


if __name__ == "__main__":
    main()
