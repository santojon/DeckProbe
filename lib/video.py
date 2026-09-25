"""Video-flow capture for DeckProbe — CDP screencast + local ffmpeg encode.

Records a CDP target's own rendered frames (`Page.startScreencast`) to local
JPEGs, then stitches them into an MP4 via a LOCAL `ffmpeg` binary — ffmpeg
never runs on the Deck itself, the same way screenshot PNGs are already
written by the local Python process, not the device.

Host-agnostic by construction: this only ever talks to whatever CDP endpoint
`DECK_CDP_HOST`/`DECK_CDP_PORT` resolves to — the same Steam debug port
regardless of whether the app under test is currently loaded via Decky
Loader or a standalone host (e.g. ShelvesHub). Nothing here assumes a
particular loader; a `target_title` substring (`"Big Picture"`,
"QuickAccess", ...) is a Steam-owned CDP target name either way.

Recording runs on a SEPARATE CDP connection, opened fresh by
`start_screencast()`, from whatever session(s) are driving the flow
(`Context.eval` / `.click()` / etc. in `deckprobe/uitests/`). This is
deliberate: `Session.call()` discards any WebSocket message that doesn't
match the call's own request id, so a screencast frame arriving while some
other call is in flight on a SHARED session would be silently dropped.
Recording gets its own socket and its own background thread so it never
competes with the calls that actually drive the test.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import threading
import time
from base64 import b64decode
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .cdp import Session, open_session, _ws_recv


class FfmpegNotFoundError(RuntimeError):
    pass


def _require_ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if not path:
        raise FfmpegNotFoundError(
            "ffmpeg not found on PATH. Video capture always encodes locally "
            "(never on the Deck) — install ffmpeg on this machine and retry."
        )
    return path


@dataclass
class Recording:
    """An in-progress screencast. Returned by `start_screencast()` — call
    `.stop()` once the flow being recorded has finished."""

    session: Session
    frames_dir: Path
    frame_count: int = 0
    _stop_event: threading.Event = field(default_factory=threading.Event)
    _thread: Optional[threading.Thread] = None
    _error: Optional[BaseException] = None

    def _run(self) -> None:
        try:
            self.session.sock.settimeout(0.5)
        except Exception:
            pass
        while not self._stop_event.is_set():
            try:
                raw = _ws_recv(self.session.sock)
            except TimeoutError:
                continue
            except OSError as e:
                self._error = e
                break
            if not raw:
                break  # connection closed
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if msg.get("method") != "Page.screencastFrame":
                continue
            params = msg.get("params") or {}
            data = params.get("data")
            session_id = params.get("sessionId")
            if data:
                self.frame_count += 1
                frame_path = self.frames_dir / f"frame_{self.frame_count:06d}.jpg"
                frame_path.write_bytes(b64decode(data))
            if session_id is not None:
                try:
                    self.session.call("Page.screencastFrameAck", {"sessionId": session_id}, timeout=2.0)
                except Exception:
                    pass  # a missed ack just risks one stalled frame, not fatal

    def stop(self, settle_seconds: float = 1.0) -> int:
        """Stop the screencast and the background drain thread. Waits
        `settle_seconds` first so a frame already in flight isn't cut off.
        Returns the total frame count. Safe to call more than once."""
        if self._thread is None:
            return self.frame_count
        time.sleep(settle_seconds)
        self._stop_event.set()
        self._thread.join(timeout=5.0)
        self._thread = None
        try:
            self.session.call("Page.stopScreencast", timeout=3.0)
        except Exception:
            pass
        self.session.close()
        return self.frame_count


def start_screencast(
    host: str,
    port: int,
    target_title: str,
    frames_dir: Path,
    *,
    max_width: int = 1280,
    max_height: int = 800,
    every_nth_frame: int = 1,
    quality: int = 80,
) -> Recording:
    """Open a dedicated CDP connection to the target matching `target_title`
    (a substring — `"Big Picture"`, `"QuickAccess"`, ...) and start streaming
    its frames as JPEGs into `frames_dir`. Returns a `Recording` — keep
    driving the flow normally on whatever other session(s) you already have
    open, then call `.stop()` when done.

    `every_nth_frame` > 1 trades frame rate for reliability — real frame
    delivery over Wi-Fi to a Deck has not been benchmarked yet (see
    deckprobe/docs/video-capture.md); start conservative (e.g. 2-3) if the
    default produces dropped/stalled frames."""
    frames_dir.mkdir(parents=True, exist_ok=True)
    session = open_session(host, port, target_title)
    session.call(
        "Page.startScreencast",
        {
            "format": "jpeg",
            "quality": quality,
            "maxWidth": max_width,
            "maxHeight": max_height,
            "everyNthFrame": every_nth_frame,
        },
        timeout=5.0,
    )
    rec = Recording(session=session, frames_dir=frames_dir)
    rec._thread = threading.Thread(target=rec._run, daemon=True)
    rec._thread.start()
    return rec


def encode_mp4(frames_dir: Path, out_path: Path, fps: int = 10) -> Path:
    """Stitch `frame_NNNNNN.jpg` files in `frames_dir` into an MP4 via a
    LOCAL `ffmpeg` (never run on the Deck). Raises `FfmpegNotFoundError` if
    ffmpeg isn't on `PATH`, and `subprocess.CalledProcessError` if encoding
    itself fails (e.g. zero frames captured)."""
    ffmpeg = _require_ffmpeg()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pattern = str(frames_dir / "frame_%06d.jpg")
    cmd = [
        ffmpeg, "-y", "-framerate", str(fps), "-i", pattern,
        # Frame dims come straight from the CDP viewport and aren't
        # guaranteed even — H.264's yuv420p needs both dimensions even.
        "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return out_path
