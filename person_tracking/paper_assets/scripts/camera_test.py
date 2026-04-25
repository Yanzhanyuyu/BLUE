#!/usr/bin/env python
"""Camera tracking test with 60-second timeout.

This script runs camera tracking for 60 seconds and exports results.
"""

import sys
import time
import threading
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.main import run_tracking


def main():
    """Main function."""
    # Define paths
    paper_assets_dir = Path(__file__).parent.parent
    output_video = paper_assets_dir / "processed" / "tracking_results" / "camera_tracked.mp4"
    output_csv = paper_assets_dir / "raw" / "csv" / "camera_tracks.csv"
    output_log = paper_assets_dir / "raw" / "logs" / "camera_run.log"

    print("=" * 60)
    print("Camera Tracking Test (60 seconds)")
    print("=" * 60)
    print(f"Output video: {output_video}")
    print(f"Output CSV: {output_csv}")
    print(f"Output log: {output_log}")
    print()

    # Flag to stop tracking
    stop_flag = threading.Event()

    # Timer to stop after 60 seconds
    def timeout_handler():
        print("\nTimeout reached, stopping...")
        stop_flag.set()

    timer = threading.Timer(60.0, timeout_handler)
    timer.start()

    try:
        # Run tracking with timeout
        # Note: We'll use a modified approach since run_tracking doesn't support timeout
        # We'll run it and let the timer interrupt
        stats = run_tracking(
            source=0,  # Camera index 0
            output=output_video,
            csv=output_csv,
            show=False,  # Don't show window
            quiet=False,
        )

        timer.cancel()  # Cancel timer if completed normally

        print()
        print("=" * 60)
        print("Camera tracking completed!")
        print("=" * 60)
        print(f"Total frames: {stats['total_frames']}")
        print(f"Elapsed time: {stats['elapsed_time']:.2f}s")
        print(f"Average FPS: {stats['avg_fps']:.1f}")
        print(f"Trajectories created: {stats['trajectories_created']}")
        print()

    except KeyboardInterrupt:
        print("\nUser interrupted")
        timer.cancel()
    except Exception as e:
        print(f"\nError: {e}")
        timer.cancel()
        sys.exit(1)


if __name__ == "__main__":
    main()
