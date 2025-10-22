import os
import numpy as np
import matplotlib.pyplot as plt
import sounddevice as sd
import soundfile as sf
from datetime import datetime
from vlf_spectrogram import plot_spectrogram

print(sd.query_devices())
sd.default.device = (1, 1)

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

def plot_spectrogram_usingmod(wav_path, timestamp):
    img_path = os.path.join(FOLDER, f"{timestamp}_spectrogram.png")
    fig, ax, f, t, Sxx = plot_spectrogram(
        wav_path,
        output=img_path,
        max_freq=MAX_FREQ,
    )
    print(f"Spectrogram saved: {img_path}")
    return img_path

def main():
    wav_path, timestamp = record_audio()
    # plot_spectrogram_usingmod(wav_path, timestamp)

if __name__ == "__main__":
    main()
