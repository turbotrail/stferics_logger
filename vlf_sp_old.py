
import argparse
import matplotlib

matplotlib.use("Agg")  # Avoid GUI backends on headless Raspberry Pi

import matplotlib.pyplot as plt
import numpy as np
import soundfile as sf
from scipy.signal import spectrogram
from config import SPEC_MAX_FREQ

def plot_spectrogram(filename, output="spectrogram.png", max_freq=SPEC_MAX_FREQ):
    # Load audio file into float32 to halve memory footprint
    data, samplerate = sf.read(filename, dtype="float32", always_2d=True)
    data = data[:, 0]  # Use first channel if stereo

    # Compute spectrogram with larger window to reduce number of frames
    f, t, Sxx = spectrogram(
        data,
        fs=samplerate,
        nperseg=2048,
        noverlap=1024,
        detrend=False,
        scaling="spectrum",
        mode="magnitude",
    )

    # Convert to log scale using float32 to keep memory usage low
    Sxx = np.maximum(Sxx.astype(np.float32, copy=False), 1e-12)
    Sxx_db = 20 * np.log10(Sxx)

    plt.figure(figsize=(10, 5))
    plt.pcolormesh(t, f, Sxx_db, shading="gouraud", cmap="inferno")
    plt.ylabel("Frequency [Hz]")
    plt.xlabel("Time [s]")
    plt.ylim([0, max_freq])
    plt.colorbar(label="Magnitude [dB]")
    plt.title("Spectrogram")
    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()
    print(f"Spectrogram saved to {output}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate spectrogram from WAV file")
    parser.add_argument("filename", help="Path to WAV file")
    parser.add_argument("--output", default="spectrogram.png", help="Output image file")
    parser.add_argument("--max_freq", type=int, default=SPEC_MAX_FREQ, help="Max frequency to display")
    args = parser.parse_args()
    plot_spectrogram(args.filename, args.filename.replace(".wav",".png"), args.max_freq)
