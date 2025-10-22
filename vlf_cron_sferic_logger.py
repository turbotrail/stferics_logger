import os
import numpy as np
import matplotlib.pyplot as plt
import sounddevice as sd
import soundfile as sf
from datetime import datetime
from vlf_spectrogram import plot_spectrogram as render_spectrogram

RECORD_SECONDS = 120  # 2 minutes
SAMPLE_RATE = 44100
THRESHOLD_DB = -100  # dB threshold for burst detection
MAX_FREQ = 10000
FOLDER = "recordings"

os.makedirs(FOLDER, exist_ok=True)

def record_audio(duration=RECORD_SECONDS, fs=SAMPLE_RATE):
    print(f"Recording {duration} seconds...")
    recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='float32')
    sd.wait()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = os.path.join(FOLDER, f"{timestamp}.wav")
    sf.write(filename, recording, fs)
    print(f"Saved: {filename}")
    return filename, timestamp

def plot_spectrogram(wav_path, timestamp):
    fig, ax, f, t, Sxx = render_spectrogram(
        wav_path,
        output=None,
        max_freq=MAX_FREQ,
        return_fig=True
    )
    Sxx_dB = 10 * np.log10(Sxx + 1e-10)

    # Detect bursts
    burst_times = []
    for i in range(Sxx_dB.shape[1]):
        if np.any(Sxx_dB[:, i] > THRESHOLD_DB):
            burst_times.append(t[i])

    # Tag burst times
    for bt in burst_times:
        ax.axvline(x=bt, color='cyan', linestyle='--', linewidth=0.5)

    img_path = os.path.join(FOLDER, f"{timestamp}_spectrogram.png")
    fig.savefig(img_path)
    plt.close(fig)
    print(f"Spectrogram saved: {img_path}")
    return img_path

def main():
    wav_path, timestamp = record_audio()
    plot_spectrogram(wav_path, timestamp)

if __name__ == "__main__":
    main()
