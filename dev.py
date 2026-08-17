#!/usr/bin/env python3
"""
KB Development Runner
---------------------
Runs Quarto Preview and Jupyter Lab concurrently while watching `nodes/`
for notebook changes to automatically regenerate `graph_output.html`.

Usage:
    uv run dev.py
    # or
    python dev.py [options]

Options:
    --no-jupyter    Skip launching Jupyter Lab
    --no-quarto     Skip launching Quarto Preview
    --no-browser    Do not auto-open browser for Jupyter / Quarto
    --anki          Also run create_anki.py on notebook changes
"""

import argparse
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
NODES_DIR = ROOT_DIR / "nodes"
VENV_DIR = ROOT_DIR / ".venv"

# ANSI Colors for clean tagged logs
COLORS = {
    "DEV": "\033[1;33m",      # Yellow
    "GRAPH": "\033[1;32m",    # Green
    "QUARTO": "\033[1;35m",   # Magenta
    "JUPYTER": "\033[1;34m",  # Blue
    "ANKI": "\033[1;36m",     # Cyan
    "ERR": "\033[1;31m",      # Red
    "RESET": "\033[0m",
}

def log(tag: str, message: str):
    color = COLORS.get(tag, COLORS["DEV"])
    reset = COLORS["RESET"]
    timestamp = time.strftime("%H:%M:%S")
    print(f"{color}[{tag.ljust(7)}] {timestamp} | {message}{reset}", flush=True)


def get_executables():
    """Find appropriate executables for python, jupyter, and quarto."""
    # Preferred python executable
    if (VENV_DIR / "bin" / "python").exists():
        py_exe = str(VENV_DIR / "bin" / "python")
    else:
        py_exe = sys.executable

    # Jupyter executable
    if (VENV_DIR / "bin" / "jupyter-lab").exists():
        jupyter_exe = str(VENV_DIR / "bin" / "jupyter-lab")
    elif (VENV_DIR / "bin" / "jupyter").exists():
        jupyter_exe = str(VENV_DIR / "bin" / "jupyter")
    else:
        jupyter_exe = shutil.which("jupyter-lab") or shutil.which("jupyter")

    # Quarto executable
    quarto_exe = shutil.which("quarto")
    if not quarto_exe and (VENV_DIR / "bin" / "quarto").exists():
        quarto_exe = str(VENV_DIR / "bin" / "quarto")

    return py_exe, jupyter_exe, quarto_exe


def run_graph_build(py_exe: str, run_anki: bool = False):
    """Run create_graph.py (and optionally create_anki.py) to rebuild artifacts."""
    graph_script = ROOT_DIR / "create_graph.py"
    if not graph_script.exists():
        log("ERR", f"Could not find {graph_script}")
        return False

    try:
        res = subprocess.run(
            [py_exe, str(graph_script)],
            cwd=str(ROOT_DIR),
            capture_output=True,
            text=True,
            check=False
        )
        if res.returncode == 0:
            log("GRAPH", "Knowledge graph rebuilt successfully -> graph_output.html")
        else:
            log("ERR", f"create_graph.py failed:\n{res.stderr.strip()}")
            return False
    except Exception as e:
        log("ERR", f"Failed to execute create_graph.py: {e}")
        return False

    if run_anki:
        anki_script = ROOT_DIR / "create_anki.py"
        if anki_script.exists():
            try:
                res = subprocess.run(
                    [py_exe, str(anki_script)],
                    cwd=str(ROOT_DIR),
                    capture_output=True,
                    text=True,
                    check=False
                )
                if res.returncode == 0:
                    log("ANKI", "Anki cards rebuilt successfully -> anki_cards.txt")
                else:
                    log("ERR", f"create_anki.py failed:\n{res.stderr.strip()}")
            except Exception as e:
                log("ERR", f"Failed to execute create_anki.py: {e}")

    return True


def get_files_snapshot():
    """Get mapping of path -> mtime for all watched files."""
    snapshot = {}
    if NODES_DIR.exists():
        for p in NODES_DIR.glob("*.ipynb"):
            try:
                snapshot[str(p)] = p.stat().st_mtime
            except OSError:
                pass

    # Also watch create_graph.py and _quarto.yml
    for extra in ["create_graph.py", "_quarto.yml", "graph.ipynb", "index.ipynb"]:
        p = ROOT_DIR / extra
        if p.exists():
            try:
                snapshot[str(p)] = p.stat().st_mtime
            except OSError:
                pass

    return snapshot


def watch_loop(py_exe: str, run_anki: bool, stop_event: threading.Event):
    """Poll filesystem for notebook/graph changes and trigger rebuild."""
    last_snapshot = get_files_snapshot()
    debounce_sec = 0.5

    while not stop_event.is_set():
        time.sleep(0.5)
        current_snapshot = get_files_snapshot()

        changes = []
        # Check modified or deleted
        for path, mtime in last_snapshot.items():
            if path not in current_snapshot:
                changes.append(f"deleted: {Path(path).name}")
            elif current_snapshot[path] > mtime:
                changes.append(f"modified: {Path(path).name}")

        # Check added
        for path in current_snapshot:
            if path not in last_snapshot:
                changes.append(f"added: {Path(path).name}")

        if changes:
            # Debounce: wait briefly for multi-file saves or notebook write completion
            time.sleep(debounce_sec)
            last_snapshot = get_files_snapshot()
            trigger_info = ", ".join(changes[:3]) + ("..." if len(changes) > 3 else "")
            log("GRAPH", f"Change detected ({trigger_info}) -> Rebuilding...")
            run_graph_build(py_exe, run_anki)
        else:
            last_snapshot = current_snapshot


def pipe_output(proc: subprocess.Popen, tag: str, stop_event: threading.Event):
    """Stream subprocess stdout/stderr line-by-line with tags."""
    if not proc.stdout:
        return
    for line in iter(proc.stdout.readline, ""):
        if stop_event.is_set():
            break
        text = line.rstrip()
        if text:
            log(tag, text)
    proc.stdout.close()


def main():
    parser = argparse.ArgumentParser(description="KB Development Runner")
    parser.add_argument("--no-jupyter", action="store_true", help="Do not launch Jupyter Lab")
    parser.add_argument("--no-quarto", action="store_true", help="Do not launch Quarto Preview")
    parser.add_argument("--no-browser", action="store_true", help="Do not auto-open browser tabs")
    parser.add_argument("--anki", action="store_true", help="Also rebuild anki_cards.txt on changes")
    args = parser.parse_args()

    py_exe, jupyter_exe, quarto_exe = get_executables()

    log("DEV", "=" * 60)
    log("DEV", "Starting KB Development Environment")
    log("DEV", f"Python executable: {py_exe}")
    log("DEV", "=" * 60)

    # Initial graph build
    log("GRAPH", "Running initial graph generation...")
    run_graph_build(py_exe, args.anki)

    processes = []
    stop_event = threading.Event()

    # Launch Quarto Preview
    if not args.no_quarto:
        if not quarto_exe:
            log("ERR", "Quarto executable not found in PATH or .venv! Skipping Quarto preview.")
        else:
            quarto_cmd = [quarto_exe, "preview"]
            if args.no_browser:
                quarto_cmd.append("--no-browser")
            log("QUARTO", f"Starting: {' '.join(quarto_cmd)}")
            try:
                proc_quarto = subprocess.Popen(
                    quarto_cmd,
                    cwd=str(ROOT_DIR),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    preexec_fn=os.setsid if sys.platform != "win32" else None
                )
                processes.append(("Quarto Preview", proc_quarto))
                threading.Thread(
                    target=pipe_output,
                    args=(proc_quarto, "QUARTO", stop_event),
                    daemon=True
                ).start()
            except Exception as e:
                log("ERR", f"Failed to start Quarto preview: {e}")

    # Launch Jupyter Lab
    if not args.no_jupyter:
        if not jupyter_exe:
            log("ERR", "Jupyter executable not found! Skipping Jupyter Lab.")
        else:
            if "jupyter-lab" in jupyter_exe:
                jupyter_cmd = [jupyter_exe]
            else:
                jupyter_cmd = [jupyter_exe, "lab"]

            if args.no_browser:
                jupyter_cmd.append("--no-browser")

            log("JUPYTER", f"Starting: {' '.join(jupyter_cmd)}")
            try:
                proc_jupyter = subprocess.Popen(
                    jupyter_cmd,
                    cwd=str(ROOT_DIR),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    preexec_fn=os.setsid if sys.platform != "win32" else None
                )
                processes.append(("Jupyter Lab", proc_jupyter))
                threading.Thread(
                    target=pipe_output,
                    args=(proc_jupyter, "JUPYTER", stop_event),
                    daemon=True
                ).start()
            except Exception as e:
                log("ERR", f"Failed to start Jupyter Lab: {e}")

    # Start File Watcher Thread
    watcher_thread = threading.Thread(
        target=watch_loop,
        args=(py_exe, args.anki, stop_event),
        daemon=True
    )
    watcher_thread.start()
    log("DEV", "Notebook watcher active. Editing any notebook will auto-update the graph & Quarto preview.")
    log("DEV", "Press Ctrl+C at any time to stop all services cleanly.")
    log("DEV", "=" * 60)

    # Shutdown handler
    def cleanup():
        if stop_event.is_set():
            return
        stop_event.set()
        log("DEV", "Stopping all services...")
        for name, proc in processes:
            if proc.poll() is None:
                log("DEV", f"Terminating {name}...")
                try:
                    if sys.platform != "win32":
                        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                    else:
                        proc.terminate()
                except Exception:
                    pass
        log("DEV", "Shutdown complete. Goodbye!")

    def sig_handler(sig, frame):
        cleanup()
        sys.exit(0)

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    # Keep main thread alive monitoring subprocesses
    try:
        while True:
            time.sleep(1)
            for name, proc in processes:
                if proc.poll() is not None:
                    # One of the processes exited unexpectedly
                    log("ERR", f"{name} exited unexpectedly with code {proc.returncode}")
    except KeyboardInterrupt:
        cleanup()


if __name__ == "__main__":
    main()
