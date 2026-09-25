"""
Lightweight test runner for the UI suite. Each test is a function that
takes a `Context` (CDP session + helpers) and returns either `None` (pass)
or raises `AssertionError` (fail). Suites group tests by feature.

Designed to read like a thin pytest-flavored harness without pulling in
pytest itself — tests run against a real Steam Deck over CDP, so the
suite never goes through CI; bare-bones is preferred over a heavy
framework dependency.
"""
from __future__ import annotations

import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from ...screenshots.lib.cdp import Session, open_session
from ...screenshots.lib import nav, capture
from ...screenshots.lib.capture import BIGPICTURE_TITLE_SUBSTRING, QAM_TITLE_SUBSTRING
from ...lib.video import start_screencast, encode_mp4, Recording, FfmpegNotFoundError


@dataclass
class Context:
    sjc: Session        # SharedJSContext — navigation, router, localStorage
    bp: Session         # Big Picture — DOM queries (DS shelves, cards, native recents)
    qam: Optional[Any]  # QuickAccess target — QAM panel DOM (separate Chromium target)
    host: str
    port: int
    out_dir: Path
    _recording: Optional[Recording] = field(default=None, repr=False)

    def eval(self, expr: str, return_by_value: bool = True, timeout: float = 8.0) -> Any:
        """Evaluate in Big Picture where DS shelves render."""
        return self.bp.evaluate(expr, return_by_value=return_by_value, timeout=timeout)

    def eval_sjc(self, expr: str, return_by_value: bool = True, timeout: float = 8.0) -> Any:
        """Evaluate in SharedJSContext (Router, appStore, settings)."""
        return self.sjc.evaluate(expr, return_by_value=return_by_value, timeout=timeout)

    def eval_qam(self, expr: str, return_by_value: bool = True, timeout: float = 8.0) -> Any:
        """Evaluate in the QuickAccess target where the QAM panel renders."""
        if self.qam is None:
            return None
        return self.qam.evaluate(expr, return_by_value=return_by_value, timeout=timeout)

    def query(self, selector: str) -> Any:
        return self.eval(f"!!document.querySelector({selector!r})")

    def text_of(self, selector: str) -> Optional[str]:
        return self.eval(
            f"(function(){{ const el = document.querySelector({selector!r}); return el ? (el.textContent || '').trim() : null; }})()"
        )

    def click(self, selector: str, settle_ms: int = 400) -> bool:
        ok = self.eval(
            f"(function(){{ const el = document.querySelector({selector!r}); if (!el) return false; el.click(); return true; }})()"
        ) is True
        time.sleep(settle_ms / 1000.0)
        return ok

    def open_qam(self, settle_ms: int = 1500) -> None:
        nav.open_qam(self.sjc, settle_ms=settle_ms)

    def close_qam(self, settle_ms: int = 600) -> None:
        nav.close_qam(self.sjc, settle_ms=settle_ms)

    def navigate(self, route: str, settle_ms: int = 1500) -> None:
        # Navigation works via m_Navigator on the GamepadUI main window instance
        # (accessible from SJC). BP and SJC Routers are either absent or separate
        # from the on-screen view — only m_Navigator.Home() reliably changes what
        # BigPicture shows.
        nav.navigate(self.sjc, route, settle_ms=settle_ms)

    def screenshot_bp(self, name: str) -> Optional[Path]:
        return capture.capture_bigpicture(self.host, self.port, self.out_dir / name)

    def screenshot_qam(self, name: str) -> Optional[Path]:
        return capture.capture_qam(self.host, self.port, self.out_dir / name)

    def start_recording(self, target: str = "bp") -> None:
        """Start a screencast of `target` ("bp" or "qam") on its own
        dedicated CDP connection — separate from the session(s) driving the
        flow, so evaluating/clicking while recording never drops frames.
        Call `stop_recording(name)` once the flow being captured is done.
        Only one recording at a time per Context; a failure to reach the
        target (e.g. QAM not open) is swallowed with a printed warning
        rather than failing the test itself."""
        if self._recording is not None:
            raise RuntimeError("a recording is already in progress — call stop_recording() first")
        title = QAM_TITLE_SUBSTRING if target == "qam" else BIGPICTURE_TITLE_SUBSTRING
        frames_dir = self.out_dir / "_frames" / f"{title.replace(' ', '_')}_{int(time.time() * 1000)}"
        try:
            self._recording = start_screencast(self.host, self.port, title, frames_dir)
        except Exception as e:
            print(f"  WARN: could not start recording ({target}): {e}")
            self._recording = None

    def stop_recording(self, name: str, fps: int = 10) -> Optional[Path]:
        """Stop the active recording (if any) and encode it to
        `<out_dir>/name` (should end in .mp4). Returns None — with a
        printed warning, never a raised exception — if nothing was
        recording, ffmpeg isn't on PATH, or zero frames were captured."""
        rec = self._recording
        self._recording = None
        if rec is None:
            return None
        count = rec.stop()
        if count == 0:
            print(f"  (0 frames captured for {name}, skipping encode)")
            return None
        out_path = self.out_dir / name
        try:
            path = encode_mp4(rec.frames_dir, out_path, fps=fps)
            print(f"  video: {path} ({count} frames)")
            return path
        except FfmpegNotFoundError as e:
            print(f"  WARN: {e}")
        except Exception as e:
            print(f"  WARN: mp4 encode failed for {name}: {e}")
        return None


@dataclass
class TestResult:
    suite: str
    name: str
    status: str  # "pass" | "fail" | "skip"
    duration_ms: int
    error: Optional[str] = None


@dataclass
class Suite:
    name: str
    tests: List[Tuple[str, Callable[[Context], None]]] = field(default_factory=list)

    def test(self, name: str):
        """Decorator: register a test function under the given name."""
        def deco(fn: Callable[[Context], None]) -> Callable[[Context], None]:
            self.tests.append((name, fn))
            return fn
        return deco


SUITES: Dict[str, Suite] = {}


def suite(name: str) -> Suite:
    """Get or create a Suite by name. Imports register tests via decorators."""
    s = SUITES.get(name)
    if s is None:
        s = Suite(name=name)
        SUITES[name] = s
    return s


class SkipTest(Exception):
    """Raise inside a test to mark it as skipped (environment not ready)."""


def _force_locale(sjc: Session, locale: str) -> None:
    """Best-effort, guarded call to `globalThis.__dsSetLocale` — the same
    hook the screenshot pipeline's `_locale.py` uses (see
    `scripts/deckprobe-ext/screenshots/scenarios/_locale.py`). A safe no-op
    for any other project reusing this generic runner without that hook."""
    if not locale:
        return
    try:
        sjc.evaluate(f"try{{globalThis.__dsSetLocale&&globalThis.__dsSetLocale({locale!r})}}catch(e){{}}")
    except Exception:
        pass


def _run_one_test(ctx: "Context", suite_name: str, test_name: str, fn, record: Optional[str], video_fps: int) -> TestResult:
    """Runs a single test function, wrapping it in `--record`'s
    start/stop_recording pair when set. Split out of `run()`'s loop so the
    suite-iteration/filtering logic there stays under the complexity cap."""
    full = f"{suite_name}.{test_name}"
    if record:
        ctx.start_recording(record)
    t0 = time.time()
    try:
        fn(ctx)
        result = TestResult(suite_name, test_name, "pass", int((time.time() - t0) * 1000))
        print(f"PASS {full}")
    except SkipTest as e:
        result = TestResult(suite_name, test_name, "skip", int((time.time() - t0) * 1000), str(e))
        print(f"SKIP {full} :: {e}")
    except AssertionError as e:
        result = TestResult(suite_name, test_name, "fail", int((time.time() - t0) * 1000), str(e))
        print(f"FAIL {full} :: {e}")
    except Exception as e:
        tb = traceback.format_exc(limit=3)
        result = TestResult(suite_name, test_name, "fail", int((time.time() - t0) * 1000), tb)
        print(f"ERROR {full} :: {e}")
    finally:
        if record:
            ctx.stop_recording(f"{full}.mp4", fps=video_fps)
    return result


def run(host: str, port: int, out_dir: Path, only: Optional[List[str]] = None,
        record: Optional[str] = None, video_fps: int = 10, locale: str = "") -> List[TestResult]:
    """`record`, when set to `"bp"` or `"qam"`, wraps EVERY test that runs
    with a screencast of that target — no suite file needs to call
    start_recording/stop_recording itself. Each test's video lands at
    `<out_dir>/<suite>.<test>.mp4`. A test can still call
    `ctx.start_recording()`/`.stop_recording()` itself for finer control
    (e.g. only part of the test, or the other target) when `record` is left
    unset.

    `locale`, when set, is forced once up front (see `_force_locale`) —
    centralised here rather than opt-in per suite (unlike screenshots' own
    per-scenario `force_locale()` calls) because `record` already wraps
    every test at this same layer — recorded flows should default to a
    known, readable language rather than whatever locale the device
    happens to be on."""
    sjc = open_session(host, port, "SharedJSContext")
    bp  = open_session(host, port, "Big Picture")
    _force_locale(sjc, locale)
    # QuickAccess session is opened lazily by qam_shelves._require_qam() after
    # open_qam() is called. Opening it at startup caused Steam to show the QAM
    # overlay, preventing the home screen from rendering its shelves.
    ctx = Context(sjc=sjc, bp=bp, qam=None, host=host, port=port, out_dir=out_dir)
    results: List[TestResult] = []
    try:
        for s in SUITES.values():
            for tname, fn in s.tests:
                full = f"{s.name}.{tname}"
                if only and not any(full.startswith(o) or s.name == o for o in only):
                    continue
                results.append(_run_one_test(ctx, s.name, tname, fn, record, video_fps))
    finally:
        sjc.close()
        bp.close()
        if ctx.qam is not None:
            try:
                ctx.qam.close()
            except Exception:
                pass
    return results
