#!/usr/bin/env python3
"""Trim local audio files and extract MP3 audio from permitted video URLs."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path


class TrimError(Exception):
    """A user-facing validation or processing error."""


def parse_timestamp(value: str) -> Decimal:
    """Parse a non-negative decimal number of seconds."""
    try:
        timestamp = Decimal(value)
    except InvalidOperation as exc:
        raise argparse.ArgumentTypeError(
            f"invalid timestamp {value!r}; use seconds such as 12.500"
        ) from exc

    if not timestamp.is_finite() or timestamp < 0:
        raise argparse.ArgumentTypeError(
            f"invalid timestamp {value!r}; use a non-negative number of seconds"
        )
    return timestamp


def run_checked(command: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, check=True, text=True, capture_output=True)
    except FileNotFoundError as exc:
        executable = command[0]
        raise TrimError(
            f"{executable!r} was not found. Install FFmpeg and ensure it is on PATH."
        ) from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "unknown FFmpeg error").strip()
        raise TrimError(f"FFmpeg failed: {detail}") from exc


def get_duration(input_path: Path) -> Decimal:
    result = run_checked(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(input_path),
        ]
    )
    try:
        seconds = json.loads(result.stdout)["format"]["duration"]
        return Decimal(str(seconds))
    except (KeyError, TypeError, ValueError, InvalidOperation) as exc:
        raise TrimError(f"Could not determine the duration of {input_path}") from exc


def trim_audio(input_path: Path, output_path: Path, start: Decimal, end: Decimal) -> None:
    if not input_path.is_file():
        raise TrimError(f"input file does not exist: {input_path}")
    if start > end:
        raise TrimError("start time must be less than or equal to end time")
    if start == end:
        raise TrimError("start and end times must define a non-empty range")

    duration = get_duration(input_path)
    if start > duration or end > duration:
        raise TrimError(
            f"timestamps exceed the file duration ({duration:.3f} seconds)"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.resolve() == input_path.resolve():
        raise TrimError("output file must be different from the input file")

    # Decimal values are passed as text so values such as 12.500 retain their
    # intended millisecond precision instead of being rounded to whole seconds.
    run_checked(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            format(start, "f"),
            "-to",
            format(end, "f"),
            "-i",
            str(input_path),
            "-map",
            "0:a:0",
            "-c:a",
            "copy",
            "-avoid_negative_ts",
            "make_zero",
            "-y",
            str(output_path),
        ]
    )


def download_youtube_audio(
    url: str,
    output_dir: Path,
    cookies_browser: str | None = None,
    cookies_file: Path | None = None,
) -> None:
    """Download audio from a permitted URL using yt-dlp and FFmpeg."""
    if shutil.which("ffmpeg") is None:
        raise TrimError("FFmpeg was not found on PATH; it is required for MP3 conversion")

    output_dir.mkdir(parents=True, exist_ok=True)
    output_template = str(output_dir / "%(title)s.%(ext)s")
    command = [
        sys.executable,
        "-m",
        "yt_dlp",
        "--no-playlist",
        "--restrict-filenames",
        "-x",
        "--audio-format",
        "mp3",
        "--audio-quality",
        "0",
        "--js-runtimes",
        "node",
        "--remote-components",
        "ejs:github",
        "-o",
        output_template,
    ]
    if cookies_browser:
        command.extend(["--cookies-from-browser", cookies_browser])
    if cookies_file:
        if not cookies_file.is_file():
            raise TrimError(f"cookies file does not exist: {cookies_file}")
        command.extend(["--cookies", str(cookies_file)])
    command.append(url)
    run_checked(
        command
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Trim an audio file using start/end times in seconds."
    )
    parser.add_argument("input", type=Path, help="input audio file")
    parser.add_argument("output", type=Path, help="output audio file")
    parser.add_argument("start", type=parse_timestamp, help="start time in seconds")
    parser.add_argument("end", type=parse_timestamp, help="end time in seconds")
    return parser


def build_download_parser(subparsers: argparse._SubParsersAction) -> None:
    download = subparsers.add_parser(
        "download",
        help="download permitted online video audio and convert it to MP3",
    )
    download.add_argument("url", help="video URL")
    download.add_argument(
        "--output-dir",
        type=Path,
        default=Path("downloads"),
        help="directory for the MP3 file (default: downloads)",
    )
    download.add_argument(
        "--cookies-from-browser",
        metavar="BROWSER",
        help="read cookies from a logged-in browser (for example brave or brave:Default)",
    )
    download.add_argument(
        "--cookies",
        type=Path,
        metavar="FILE",
        help="read cookies from a Netscape-format cookie file",
    )


def main() -> int:
    # Preserve the original four-positional-argument interface while adding
    # an explicit subcommand for online downloads.
    if len(sys.argv) > 1 and sys.argv[1] == "download":
        parser = argparse.ArgumentParser(description="Download permitted video audio as MP3.")
        subparsers = parser.add_subparsers(dest="command", required=True)
        build_download_parser(subparsers)
        args = parser.parse_args()
        if shutil.which("ffmpeg") is None:
            print("error: FFmpeg must be installed and available on PATH", file=sys.stderr)
            return 2
        try:
            download_youtube_audio(
                args.url,
                args.output_dir,
                args.cookies_from_browser,
                args.cookies,
            )
        except TrimError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(f"MP3 saved in {args.output_dir.resolve()}")
        return 0

    args = build_parser().parse_args()
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        print("error: FFmpeg and FFprobe must both be installed and available on PATH", file=sys.stderr)
        return 2
    try:
        trim_audio(args.input, args.output, args.start, args.end)
    except TrimError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Created {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
