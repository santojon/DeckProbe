"""Video-capture helper for scenario authors — thin wrapper around
deckprobe.lib.video (CDP screencast + local ffmpeg encode), matching the
screenshot scenarios' single-call ergonomics (`capture_bigpicture(...)`)."""
from __future__ import annotations

import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from deckprobe.lib.video import start_screencast, encode_mp4


@contextmanager
def record(host: str, port: int, target_title: str, out_dir: Path, name: str, *, fps: int = 10) -> Iterator[None]:
    """Records `target_title`'s CDP screencast (`"Big Picture"`, `"QuickAccess"`,
    ...) for the duration of the `with` block, encoding to `<out_dir>/<name>`
    (should end in .mp4) on exit. Drive the flow inside the block on a
    session you already hold (`sjc`, or a fresh one) — never on this
    recording connection itself, which deckprobe.lib.video keeps separate
    on purpose (see its module docstring). A no-op encode (nothing written)
    when zero frames were captured, so a failed/empty recording doesn't
    crash the scenario or leave a corrupt .mp4."""
    frames_dir = out_dir / "_frames" / f"{name.replace('/', '_')}_{int(time.time() * 1000)}"
    rec = start_screencast(host, port, target_title, frames_dir)
    try:
        yield
    finally:
        frame_count = rec.stop()
        if frame_count > 0:
            encode_mp4(frames_dir, out_dir / name, fps=fps)
