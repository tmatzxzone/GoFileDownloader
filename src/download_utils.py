"""Utilities for handling file downloads with compact progress tracking."""

import logging
import time
from pathlib import Path

from requests import Response
from tqdm.auto import tqdm

from src.managers.progress_manager import ProgressManager
from .config import LARGE_FILE_CHUNK_SIZE, THRESHOLDS


def get_chunk_size(file_size: int) -> int:
    """Determine the optimal chunk size based on the file size."""
    for threshold, chunk_size in THRESHOLDS:
        if file_size < threshold:
            return chunk_size
    return LARGE_FILE_CHUNK_SIZE


def save_file_with_progress(
    response: Response,
    download_path: str,
    task: int,
    progress_manager: ProgressManager,
) -> None:
    """Save a file while showing one compact progress bar and transfer speed."""
    file_size = int(response.headers.get("Content-Length", -1))
    if file_size < 0:
        logging.warning("Content length not provided for %s", download_path)

    chunk_size = get_chunk_size(file_size) if file_size >= 0 else LARGE_FILE_CHUNK_SIZE
    total_downloaded = 0
    start_time = time.monotonic()

    # tqdm.auto uses a notebook widget in Colab when available, avoiding a new
    # output line for every update. In a terminal it falls back to a text bar.
    with Path(download_path).open("wb") as file, tqdm(
        total=file_size if file_size >= 0 else None,
        initial=0,
        desc=Path(download_path).name[:32],
        unit="B",
        unit_scale=True,
        unit_divisor=1024,
        dynamic_ncols=True,
        mininterval=0.5,
        leave=True,
    ) as progress:
        for chunk in response.iter_content(chunk_size=chunk_size):
            if not chunk:
                continue
            file.write(chunk)
            total_downloaded += len(chunk)
            progress.update(len(chunk))
            # Keep the existing internal progress manager updated for compatibility.
            if file_size > 0:
                completed = min(100, (total_downloaded / file_size) * 100)
                progress_manager.update_task(task, completed=completed)

    elapsed = max(time.monotonic() - start_time, 0.001)
    speed = total_downloaded / elapsed
    if speed >= 1024 ** 2:
        speed_text = f"{speed / (1024 ** 2):.2f} MB/s"
    elif speed >= 1024:
        speed_text = f"{speed / 1024:.2f} KB/s"
    else:
        speed_text = f"{speed:.0f} B/s"
    print(f"Finished: {Path(download_path).name} — {speed_text}")
