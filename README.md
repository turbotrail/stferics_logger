# stferics_logger

Continuous VLF audio recorder for capturing sferics/whistlers using a Raspberry Pi and a sound card. The system records every night from 18:00 to 06:00 local time, splitting the session into 12 hourly WAV files. A GitHub Actions workflow (running on a self‑hosted Pi runner) installs dependencies and configures a cron job to trigger the recorder nightly.

## Features
- Nightly window: records 18:00 → 06:00 local time
- Hourly segments: 12 × 1‑hour WAV files per night
- Streaming write: low memory footprint during long recordings
- Self‑hosted workflow: GitHub Actions sets up Python env and cron on the Pi
- Optional spectrogram generation function available (script prepared, off by default)

## Repository Layout
- `vlf_cron_sferic_logger.py`: Nightly recorder entrypoint (waits until 18:00, records until 06:00, 1‑hour splits)
- `vlf_spectrogram.py`: Utility to generate spectrogram images from WAV files
- `requirements.txt`: Python dependencies
- `.github/workflows/vlf-cron.yml`: GitHub Actions workflow that installs deps and configures the Pi’s cron
- `recordings/`: Output folder for WAV files (created on first run)
- `~/stferics_logger/logs/vlf.log`: Log file on the Pi (created by the workflow’s cron command)

## Hardware & OS
- Raspberry Pi 4 (self‑hosted GitHub Actions runner)
- USB sound card / ADC capable of the desired sampling rate
- Raspberry Pi OS/Debian with `cron`, Python 3.9+ recommended

## Software Dependencies
- Python packages: `numpy`, `matplotlib`, `scipy`, `sounddevice`, `soundfile`
- Installed automatically by the workflow’s virtual environment step or manually via:
  - `pip install -r requirements.txt`

## Local Setup (Manual)
1. Clone the repo on the Pi: `git clone https://github.com/<you>/stferics_logger.git`
2. Create and activate a venv:
   - `python3 -m venv venv`
   - `source venv/bin/activate`
3. Install dependencies: `pip install -r requirements.txt`
4. Verify/list available audio devices: run `python -c "import sounddevice as sd; print(sd.query_devices())"`
5. Adjust input device indices in `vlf_cron_sferic_logger.py` if needed (search for `sd.default.device = (1, 1)`).
6. Run the recorder manually to test:
   - `python vlf_cron_sferic_logger.py`
   - The script waits until the next 18:00 local time. For a quick test, temporarily change the start time in the script or run during the window.

## How the Nightly Recorder Works
- The script computes the next 18:00 local time and sleeps until then.
- It records continuously until 06:00 next day.
- It splits the run into 1‑hour WAV files named by the segment start timestamp, e.g., `recordings/20241022_180000.wav`.
- Sampling parameters:
  - Sample rate: 44100 Hz (changeable)
  - Channels: 1
  - WAV subtype: PCM_16

## GitHub Actions: Self‑Hosted Runner + Cron
This repo includes a workflow that configures the Pi’s cron to run the recorder nightly.

File: `.github/workflows/vlf-cron.yml`
- Checks out the repo on the self‑hosted Pi runner.
- Syncs files to `~/stferics_logger` (persistent location on the Pi).
- Creates a Python virtual environment and installs dependencies.
- Adds/updates a cron entry to start the recorder at 18:00 daily:
  - `0 18 * * * cd $HOME/stferics_logger && $HOME/stferics_logger/venv/bin/python vlf_cron_sferic_logger.py >> $HOME/stferics_logger/logs/vlf.log 2>&1`

Triggering the workflow:
- Push to `main`, or use the “Run workflow” button under Actions → Configure VLF Cron.

Logs:
- Recorder output: `~/stferics_logger/logs/vlf.log`
- Cron/service events: `sudo journalctl -u cron` or `sudo grep CRON /var/log/syslog`

## Spectrograms (Optional)
To generate spectrograms for a recorded WAV file:
- `python vlf_spectrogram.py path/to/audio.wav --output path/to/output.png --max_freq 10000`

Note: The main recorder doesn’t auto‑generate spectrograms by default to keep runtime light. You can integrate it after each segment if desired.

## Troubleshooting
- No audio captured / silent WAVs:
  - Check device indices printed at start; update `sd.default.device` in `vlf_cron_sferic_logger.py`.
  - Ensure input gain and wiring are correct on the sound card.
- Cron didn’t run:
  - Confirm crontab contains the expected line: `crontab -l | grep vlf_cron_sferic_logger.py`
  - Check logs at `~/stferics_logger/logs/vlf.log`.
  - Inspect cron service: `sudo systemctl status cron` and `sudo journalctl -u cron`.
- Permissions/storage:
  - Ensure `~/stferics_logger` is writable by the runner user.
  - Monitor disk usage: hourly WAVs can be large; rotate or offload as needed.

## License
See `LICENSE` for details.
