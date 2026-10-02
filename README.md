# Audio Trimmer CLI

A small Python command-line tool that trims an audio file using decimal-second timestamps, including millisecond values such as `12.500` and `45.750`.

## Requirements

- Python 3.9 or newer
- FFmpeg, including `ffprobe`, available on your `PATH`

Install FFmpeg:

- Windows: install it from [ffmpeg.org](https://ffmpeg.org/download.html), then add its `bin` directory to `PATH`.
- macOS: `brew install ffmpeg`
- Debian/Ubuntu: `sudo apt update && sudo apt install ffmpeg`

Install the Python dependency for online audio extraction:

```powershell
python -m pip install -r requirements.txt
```

Recent YouTube downloads also require a JavaScript runtime. This project uses
Node.js; install Node.js 22 or newer and confirm it is available with
`node --version`. The downloader enables Node.js and the yt-dlp EJS challenge
scripts automatically.

## Usage

```text
python audio_trimmer.py input.mp3 output.mp3 12.500 45.750
```

The tool validates that the input exists, the range is valid, and both timestamps fit within the source duration. FFmpeg stream-copy mode is used so the audio is not re-encoded or intentionally degraded.

For help:

```text
python audio_trimmer.py --help
```

## Download permitted online video audio

If you own the video or have permission to download it, extract its audio as
an MP3 with:

```powershell
python audio_trimmer.py download "https://www.youtube.com/watch?v=VIDEO_ID" --output-dir downloads
```

The command uses `yt-dlp` for the download and FFmpeg for MP3 conversion. Use
it only for content you are authorized to download, and follow the source
platform's terms.

For an age-restricted video, first sign in to YouTube in your browser, close
the browser completely, and pass the browser name:

```powershell
python audio_trimmer.py download "https://www.youtube.com/watch?v=Rfe2SbMgovQ" --cookies-from-browser chrome --output-dir downloads
```

Replace `chrome` with `edge`, `firefox`, or another supported browser. If you
use a non-default profile, use a value such as `brave:Profile 1`. Cookies are
read locally and are not uploaded by this tool.

If Chromium-based browser decryption fails with a Windows DPAPI error, try
Firefox instead:

```powershell
python audio_trimmer.py download "https://www.youtube.com/watch?v=Rfe2SbMgovQ" --cookies-from-browser firefox --output-dir downloads
```

As another fallback, create a Netscape-format cookie file using yt-dlp, then
pass it to this tool:

```powershell
python -m yt_dlp --cookies-from-browser firefox --cookies youtube-cookies.txt "https://www.youtube.com/watch?v=Rfe2SbMgovQ"
python audio_trimmer.py download "https://www.youtube.com/watch?v=Rfe2SbMgovQ" --cookies youtube-cookies.txt --output-dir downloads
```

Treat cookie files like passwords and delete them after use.

Note: stream copying preserves quality, but compressed audio formats can only be cut on their encoded packet boundaries. If sample-perfect cuts are more important than avoiding re-encoding, the FFmpeg command can be adapted to decode and re-encode the audio.
