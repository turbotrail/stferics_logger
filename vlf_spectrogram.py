
import argparse
import matplotlib.pyplot as plt
import numpy as np
import soundfile as sf
from scipy.signal import spectrogram

def plot_spectrogram(filename, output="spectrogram.png", max_freq=10000):
    # Load audio file
    data, samplerate = sf.read(filename)
    if data.ndim > 1:
        data = data[:, 0]  # Use first channel if stereo

    # Compute spectrogram
    f, t, Sxx = spectrogram(data, fs=samplerate, nperseg=1024, noverlap=512)
    plt.figure(figsize=(12, 6))
    plt.pcolormesh(t, f, 10 * np.log10(Sxx), shading="gouraud", cmap="inferno")
    plt.ylabel("Frequency [Hz]")
    plt.xlabel("Time [s]")
    plt.ylim([0, max_freq])
    plt.colorbar(label="Power [dB]")
    plt.title("Spectrogram")
    plt.tight_layout()
    plt.savefig(output)
    print(f"Spectrogram saved to {output}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate spectrogram from WAV file")
    parser.add_argument("filename", help="Path to WAV file")
    parser.add_argument("--output", default="spectrogram.png", help="Output image file")
    parser.add_argument("--max_freq", type=int, default=10000, help="Max frequency to display")
    args = parser.parse_args()
    plot_spectrogram(args.filename, args.output, args.max_freq)
