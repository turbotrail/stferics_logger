import os
import queue
from datetime import datetime, timedelta

import numpy as np
import sounddevice as sd
import soundfile as sf

from config import (
    SAMPLE_RATE,
    CHANNELS,
    OUTPUT_FOLDER as FOLDER,
    WINDOW_START,
    WINDOW_END,
    TOTAL_HOURS,
    SEGMENT_HOURS,
    LIST_DEVICES_ON_START,
    get_device_tuple,
)


# Configure input/output devices from environment if provided
try:
    if LIST_DEVICES_ON_START:
        print(sd.query_devices())
    device_tuple = get_device_tuple()
    if device_tuple is not None:
        sd.default.device = device_tuple
except Exception as e:
    print(f"Audio device setup warning: {e}")


os.makedirs(FOLDER, exist_ok=True)


def next_window_start(now: datetime) -> datetime:
    """Return the next datetime at 18:00 local time from 'now'."""
    today_start = datetime.combine(now.date(), WINDOW_START)
    if now <= today_start:
        return today_start
    # Otherwise next day 18:00
    return today_start + timedelta(days=1)


def window_end_for(start_dt: datetime) -> datetime:
    """Given a start at 18:00, return the end (next day at 06:00)."""
    # Start is always at 18:00, so end is next day 06:00
    next_day = start_dt.date() + timedelta(days=1)
    return datetime.combine(next_day, WINDOW_END)


def timestamp_for_file(dt: datetime) -> str:
    return dt.strftime("%Y%m%d_%H%M%S")


def record_stream_to_file(filename: str, duration_seconds: int, fs: int = SAMPLE_RATE, channels: int = CHANNELS):
    """
    Record audio using a streaming callback and write directly to disk to avoid
    large memory allocations. Stops after duration_seconds.
    """
    q: queue.Queue[np.ndarray] = queue.Queue()

    def callback(indata, frames, time_info, status):
        if status:
            print(f"Stream status: {status}")
        # Copy to avoid referencing underlying buffer
        q.put(indata.copy())

    frames_to_write = duration_seconds * fs
    written = 0

    with sf.SoundFile(
        filename,
        mode="w",
        samplerate=fs,
        channels=channels,
        subtype="PCM_16",
    ) as file, sd.InputStream(
        samplerate=fs,
        channels=channels,
        dtype="float32",
        callback=callback,
    ):
        print(f"Recording to {filename} for {duration_seconds} seconds...")
        while written < frames_to_write:
            data = q.get()
            # Ensure we don't exceed the intended duration
            remaining = frames_to_write - written
            if len(data) > remaining:
                data = data[:remaining]
            file.write(data)
            written += len(data)
        print(f"Saved: {filename}")


def run_night_recording():
    now = datetime.now()
    start_dt = next_window_start(now)
    if now < start_dt:
        wait = (start_dt - now).total_seconds()
        print(f"Waiting until window start at {start_dt} (~{int(wait)}s)...")
        # Busy-wait with sleep intervals to keep simple and portable
        import time as _time
        while True:
            now = datetime.now()
            if now >= start_dt:
                break
            _time.sleep(min(60, max(1, int((start_dt - now).total_seconds()))))

    end_dt = window_end_for(start_dt)
    print(f"Recording window: {start_dt} -> {end_dt} ({TOTAL_HOURS} hours)")

    segment_seconds = SEGMENT_HOURS * 3600
    segment_start = start_dt
    segments = 0

    while segment_start < end_dt and segments < TOTAL_HOURS:
        segment_end = min(segment_start + timedelta(hours=SEGMENT_HOURS), end_dt)
        duration = int((segment_end - segment_start).total_seconds())
        ts = timestamp_for_file(segment_start)
        filename = os.path.join(FOLDER, f"{ts}.wav")
        try:
            record_stream_to_file(filename, duration_seconds=duration)
        except Exception as e:
            print(f"Error during recording for segment starting {segment_start}: {e}")
        segment_start = segment_end
        segments += 1

    print("Night recording complete.")


def main():
    run_night_recording()


if __name__ == "__main__":
    main()
