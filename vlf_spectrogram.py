
import argparse
import os
import tempfile
import matplotlib

matplotlib.use("Agg")  # Avoid GUI backends on headless Raspberry Pi

import matplotlib.pyplot as plt
import numpy as np
import soundfile as sf
from scipy.signal import spectrogram
from config import (
    SPEC_MAX_FREQ,
    SPEC_NPERSEG,
    SPEC_NOVERLAP,
    SPEC_BLOCK_SECONDS,
    SPEC_PLOW,
    SPEC_PHIGH,
    SPEC_DB_RANGE,
    SPEC_COLORMAP,
)


def _compute_spectrogram_chunk(x, samplerate, nperseg, noverlap):
    # Compute magnitude spectrogram for a chunk (no detrend, Hann window default)
    f, t, Sxx = spectrogram(
        x,
        fs=samplerate,
        nperseg=nperseg,
        noverlap=noverlap,
        detrend=False,
        scaling="spectrum",
        mode="magnitude",
    )
    return f, t, Sxx


def plot_spectrogram(filename, output="spectrogram.png", max_freq=SPEC_MAX_FREQ,
                     nperseg=SPEC_NPERSEG, noverlap=SPEC_NOVERLAP, block_seconds=SPEC_BLOCK_SECONDS,
                     plow=SPEC_PLOW, phigh=SPEC_PHIGH, db_range=SPEC_DB_RANGE, colormap=SPEC_COLORMAP,
                     start_sec=None, duration_sec=None, last_minutes=None):
    """
    Streamed, low‑memory spectrogram.

    - Reads the WAV file in small blocks (no full-file load)
    - Computes STFT per block with proper overlap carry
    - Stores dB values in a disk-backed memmap to keep RAM flat
    - Renders final image using the memmap to avoid large arrays in memory
    """

    info = sf.info(filename)
    samplerate = info.samplerate
    channels = info.channels
    total_samples = info.frames
    total_duration_sec = total_samples / float(samplerate) if samplerate else 0.0

    # Determine segment to process
    if last_minutes is not None:
        try:
            duration_sec = float(last_minutes) * 60.0
        except Exception:
            duration_sec = None
        start_sec = max(0.0, total_duration_sec - (duration_sec or 0.0))
    else:
        start_sec = 0.0 if start_sec is None else float(start_sec)
        duration_sec = None if duration_sec is None else float(duration_sec)

    start_frame = int(start_sec * samplerate)
    if start_frame >= total_samples:
        raise ValueError("start_sec is beyond end of file")
    frames_available = max(0, total_samples - start_frame)
    segment_frames = frames_available if duration_sec is None else min(int(duration_sec * samplerate), frames_available)
    if segment_frames <= 0:
        raise ValueError("No audio to process in the requested segment")

    hop = nperseg - noverlap
    if hop <= 0:
        raise ValueError("noverlap must be smaller than nperseg")

    # Expected number of time frames for the selected segment
    if segment_frames >= nperseg:
        n_time = 1 + (segment_frames - nperseg) // hop
    else:
        n_time = 1  # one frame when padding isn't used; may yield 0 later

    n_freq = nperseg // 2 + 1

    # Prepare memmap to hold dB values (float32). This keeps RAM usage low.
    tmp_dir = os.path.dirname(os.path.abspath(output)) or "."
    tmp_memmap_path = os.path.join(
        tmp_dir,
        f".{os.path.basename(output)}.spectrogram.memmap"
    )

    # Clean any stale memmap
    try:
        if os.path.exists(tmp_memmap_path):
            os.remove(tmp_memmap_path)
    except OSError:
        pass

    spec_mm = np.memmap(tmp_memmap_path, mode="w+", dtype=np.float32, shape=(n_freq, max(n_time, 1)))

    # Stream through the audio
    frames_per_block = max(int(block_seconds * samplerate), nperseg)
    frame_cursor = 0
    carry = np.zeros(0, dtype=np.float32)

    with sf.SoundFile(filename, mode="r") as snd:
        snd.seek(start_frame)
        frames_read = 0
        while frames_read < segment_frames:
            to_read = min(frames_per_block, segment_frames - frames_read)
            # Read a block (always_2d to handle multi-channel uniformly)
            block = snd.read(frames=to_read, dtype="float32", always_2d=True)
            if block.size == 0:
                break
            frames_read += block.shape[0]
            # Mixdown to mono by taking first channel
            x = block[:, 0]

            # Prepend carry from previous block to ensure correct overlap continuity
            if carry.size > 0:
                x = np.concatenate([carry, x])

            # How many full frames can we form from this buffer?
            if x.size >= nperseg:
                n_frames = 1 + (x.size - nperseg) // hop
                used_len = nperseg + (n_frames - 1) * hop
            else:
                n_frames = 0
                used_len = 0

            if n_frames > 0:
                f, t_chunk, Sxx = _compute_spectrogram_chunk(x[:used_len], samplerate, nperseg, noverlap)
                # Convert to dB
                Sxx = np.maximum(Sxx.astype(np.float32, copy=False), 1e-12)
                Sxx_db = 20.0 * np.log10(Sxx)

                # Write into memmap; handle potential slight mismatch at the tail
                end_cursor = min(frame_cursor + Sxx_db.shape[1], spec_mm.shape[1])
                spec_mm[:, frame_cursor:end_cursor] = Sxx_db[:, : end_cursor - frame_cursor]
                frame_cursor = end_cursor

                # Keep last noverlap samples for next block continuity
                carry = x[used_len - noverlap:used_len].copy()
            else:
                # Not enough samples to form a frame yet; accumulate in carry
                carry = x.copy()

            # Safety: break if we've filled expected frames
            if frame_cursor >= spec_mm.shape[1]:
                break

    # Determine frequency index limit for max_freq
    f_bins = np.fft.rfftfreq(nperseg, d=1.0 / samplerate)
    max_freq = float(max_freq)
    f_mask = f_bins <= max_freq
    f_bins = f_bins[f_mask]

    # Dynamic color scaling for better contrast in weak signals
    img_view = spec_mm[:, :frame_cursor]
    finite_mask = np.isfinite(img_view)
    if np.any(finite_mask):
        if db_range is not None:
            vmax = float(np.nanpercentile(img_view[finite_mask], phigh))
            vmin = vmax - float(db_range)
        else:
            vmin = float(np.nanpercentile(img_view[finite_mask], plow))
            vmax = float(np.nanpercentile(img_view[finite_mask], phigh))
        if not np.isfinite(vmin):
            vmin = float(np.nanmin(img_view))
        if not np.isfinite(vmax):
            vmax = float(np.nanmax(img_view))
        if vmin >= vmax:
            vmax = vmin + 1.0
    else:
        vmin, vmax = -120.0, 0.0

    duration_sec_plotted = segment_frames / float(samplerate)

    # Plot using imshow to avoid generating a giant quadmesh in memory
    plt.figure(figsize=(10, 5))
    extent = [start_sec, start_sec + duration_sec_plotted, f_bins[0] if f_bins.size else 0.0, f_bins[-1] if f_bins.size else max_freq]
    # Slice to selected frequency range and produced frames only
    img_data = spec_mm[f_mask, :frame_cursor]
    plt.imshow(
        img_data,
        origin="lower",
        aspect="auto",
        extent=extent,
        interpolation="nearest",
        cmap=colormap,
        vmin=vmin,
        vmax=vmax,
    )
    plt.ylabel("Frequency [Hz]")
    plt.xlabel("Time [s]")
    plt.ylim([0, max_freq])
    cbar = plt.colorbar()
    cbar.set_label("Magnitude [dB]")
    plt.title("Spectrogram")
    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()

    # Clean up memmap file
    try:
        del spec_mm  # ensure file is closed on Windows
    except Exception:
        pass
    try:
        if os.path.exists(tmp_memmap_path):
            os.remove(tmp_memmap_path)
    except OSError:
        pass

    print(f"Spectrogram saved to {output}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate spectrogram from WAV file")
    parser.add_argument("filename", help="Path to WAV file")
    parser.add_argument("--output", default="spectrogram.png", help="Output image file")
    parser.add_argument("--max_freq", type=int, default=SPEC_MAX_FREQ, help="Max frequency to display")
    parser.add_argument("--nperseg", type=int, default=SPEC_NPERSEG, help="STFT window size (try 1024 or 512 for sferics)")
    parser.add_argument("--noverlap", type=int, default=SPEC_NOVERLAP, help="STFT overlap (e.g., 768 for nperseg=1024)")
    parser.add_argument("--block_seconds", type=float, default=SPEC_BLOCK_SECONDS, help="Streaming block duration (s)")
    parser.add_argument("--plow", type=float, default=SPEC_PLOW, help="Lower percentile for auto scaling")
    parser.add_argument("--phigh", type=float, default=SPEC_PHIGH, help="Upper percentile for auto scaling")
    parser.add_argument("--db_range", type=float, default=SPEC_DB_RANGE, help="If set, use fixed dB range (vmin=vmax-dB)")
    parser.add_argument("--colormap", default=SPEC_COLORMAP, help="Matplotlib colormap (e.g., inferno, viridis)")
    # Time cropping
    parser.add_argument("--start_sec", type=float, default=None, help="Start time (s) from beginning of file")
    parser.add_argument("--duration_sec", type=float, default=None, help="Duration (s) to process from start_sec")
    parser.add_argument("--last_minutes", type=float, default=None, help="Convenience: process only the last N minutes")
    args = parser.parse_args()
    # Use provided output path as-is
    out = args.filename.replace(".wav", "_spectrogram.png")
    plot_spectrogram(
        args.filename,
        output=out,
        max_freq=args.max_freq,
        nperseg=args.nperseg,
        noverlap=args.noverlap,
        block_seconds=args.block_seconds,
        plow=args.plow,
        phigh=args.phigh,
        db_range=args.db_range,
        colormap=args.colormap,
        start_sec=args.start_sec,
        duration_sec=args.duration_sec,
        last_minutes=args.last_minutes,
    )
