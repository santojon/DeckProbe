#!/usr/bin/env python3
"""Generic deckprobe CLI.

Usage:
  cli.py probe [--mode smoke|rows|mount]
  cli.py screenshot [--keep-existing] [--locale LOCALE]
  cli.py diag list [--extra-dir <path>]
  cli.py diag run <script>

`diag list`/`run` look in deckprobe/diag/ AND in directories listed in
DECKPROBE_DIAG_DIRS (colon-separated) or via --extra-dir, so projects can
keep their app-specific diag scripts outside the deckprobe tree.
"""
import argparse
import subprocess
import sys
import os

# Load .env + deckprobe.config.json early so subcommands and subprocesses
# inherit every override. Falls back to DECK_HOST for DECK_CDP_HOST too.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.config import bootstrap as _deckprobe_bootstrap  # noqa: E402
_deckprobe_bootstrap()

HERE = os.path.dirname(os.path.abspath(__file__))

def run_probe(args):
    mode = args.mode or "smoke"
    # probe script may be in tools/ after reorg
    candidates = [os.path.join(HERE, "tools", "cdp_probe.py"), os.path.join(HERE, "cdp_probe.py"), os.path.join(HERE, "tools", "cdp_probe.py")]
    path = next((c for c in candidates if os.path.isfile(c)), None)
    if not path:
        print('cdp_probe.py not found', file=sys.stderr); return 2
    cmd = [sys.executable, path, "--mode", mode]
    return subprocess.run(cmd).returncode

def _resolve_anchored(p):
    """Anchor a relative path against the parent repo root so values
    coming from `deckprobe.config.json` (which are workspace-relative)
    resolve correctly regardless of cwd."""
    if not p:
        return ''
    if os.path.isabs(p):
        return p
    repo_root = os.path.abspath(os.path.join(HERE, '..'))
    return os.path.join(repo_root, p)


def run_screenshot(args):
    # Drives the modular runner (deckprobe.screenshots.run), loading project
    # scenarios from the configured scenarios dir. Run as a module from the
    # repo root so the package's relative imports resolve regardless of how
    # deep deckprobe is vendored.
    repo_root = os.path.abspath(os.path.join(HERE, '..'))
    scenarios_dir = _resolve_anchored(
        args.scenarios_dir or os.environ.get('DECKPROBE_SCREENSHOTS_SCENARIOS_DIR', '')
    )
    out_dir = _resolve_anchored(os.environ.get('DECKPROBE_SCREENSHOTS_DIR', '') or 'assets/screenshots')
    host = os.environ.get('DECK_CDP_HOST') or os.environ.get('DECK_HOST') or 'localhost'
    port = os.environ.get('DECK_CDP_PORT', '8081')
    cmd = [sys.executable, '-m', 'deckprobe.screenshots.run',
           '--host', host, '--port', str(port), '--out', out_dir]
    if scenarios_dir:
        cmd += ['--scenarios-dir', scenarios_dir]
    if args.only:
        cmd += ['--only', args.only]
    return subprocess.run(cmd, cwd=repo_root).returncode

def _diag_dirs(extra_dir):
    dirs = [os.path.join(HERE, 'diag')]
    extra_env = os.environ.get('DECKPROBE_DIAG_DIRS', '')
    if extra_env:
        for p in extra_env.split(':'):
            if p:
                dirs.append(_resolve_anchored(p))
    if extra_dir:
        dirs.append(_resolve_anchored(extra_dir))
    return [d for d in dirs if os.path.isdir(d)]

def list_diags(args):
    seen = set()
    for d in _diag_dirs(getattr(args, 'extra_dir', '')):
        for f in sorted(os.listdir(d)):
            if f in seen:
                continue
            seen.add(f)
            print(f)
    return 0

def run_diag(args):
    name = args.script
    candidates = []
    for d in _diag_dirs(getattr(args, 'extra_dir', '')):
        candidates.extend(os.path.join(d, f) for f in os.listdir(d) if name in f)
    if not candidates:
        p = os.path.join(HERE, name)
        if os.path.isfile(p): candidates = [p]
    if not candidates:
        print('Script not found:', name, file=sys.stderr)
        return 2
    path = candidates[0]
    if path.endswith('.py'):
        return subprocess.run([sys.executable, path]).returncode
    return subprocess.run(['node', path]).returncode

def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='cmd')

    p_probe = sub.add_parser('probe')
    p_probe.add_argument('--mode', choices=['mount','rows','smoke'], default='smoke')
    p_probe.set_defaults(func=run_probe)

    p_ss = sub.add_parser('screenshot')
    p_ss.add_argument('--only', default='', help='Comma-separated scenario names to run (default: all).')
    p_ss.add_argument('--scenarios-dir', default='', help='Dir with @register scenario *.py files (also DECKPROBE_SCREENSHOTS_SCENARIOS_DIR env / deckprobe.config.json `screenshots_scenarios_dir`).')
    p_ss.set_defaults(func=run_screenshot)

    p_diag = sub.add_parser('diag')
    p_diag_sub = p_diag.add_subparsers(dest='diagcmd')
    p_diag_list = p_diag_sub.add_parser('list')
    p_diag_list.add_argument('--extra-dir', default='', help='Extra diag dir to scan (also DECKPROBE_DIAG_DIRS env, colon-separated).')
    p_diag_list.set_defaults(func=list_diags)
    p_diag_run = p_diag_sub.add_parser('run')
    p_diag_run.add_argument('script')
    p_diag_run.add_argument('--extra-dir', default='')
    p_diag_run.set_defaults(func=run_diag)

    args = p.parse_args()
    if not hasattr(args, 'func'):
        p.print_help()
        return 1
    return args.func(args)

if __name__ == '__main__':
    sys.exit(main())
