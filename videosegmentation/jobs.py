"""Detached jobs inside the current runtime, with logs and status on Drive."""

import json
import os
import subprocess
import sys
import threading
import uuid
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

from .storage import dataset_directory


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _boot_id():
    path = Path("/proc/sys/kernel/random/boot_id")
    return path.read_text().strip() if path.exists() else None


def _process_start(pid):
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        return None if fields[0] == "Z" else fields[19]
    except (OSError, IndexError):
        return None


def _save(path, data):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=2) + "\n")
    temporary.replace(path)


def update_job(path, status, exit_code=None):
    if path is None:
        return
    data = json.loads(path.read_text())
    data.update(status=status, updated_at=_now(), pid=os.getpid(), boot_id=_boot_id(), process_start=_process_start(os.getpid()))
    if exit_code is not None:
        data["exit_code"] = exit_code
    _save(path, data)


def launch(argv, args):
    name = args.name if args.dataset == "extract" else args.downloader.folder_name
    dataset = dataset_directory(args.root, name)
    jobs = dataset / "jobs"
    jobs.mkdir(exist_ok=True)
    identifier = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ") + "-" + uuid.uuid4().hex[:8]
    record = jobs / (identifier + ".json")
    log = jobs / (identifier + ".log")
    _save(record, {"dataset": name, "status": "starting", "created_at": _now(), "log": str(log)})
    child = [arg for arg in argv if arg != "--background"]
    command = [sys.executable, "-u", "-m", "videosegmentation", *child, "--_job-file", str(record)]
    try:
        with log.open("ab", buffering=0) as output:
            process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
    except OSError:
        update_job(record, "failed-to-start", 1)
        raise
    # Reap children when called from a long-lived notebook kernel, without making
    # a command-line launcher wait for the detached job to finish.
    threading.Thread(target=process.wait, daemon=True).start()
    print(f"Started background job (current runtime only), PID: {process.pid}")
    print(f"Log: {log}")
    print(f"Status: python download.py status --name {name} --root {args.root}")
    return 0


def show_status(args):
    directory = Path(args.root).expanduser() / args.name / "jobs"
    records = sorted(directory.glob("*.json"))
    if not records:
        print(f"No saved jobs in {directory}")
        return 0
    data = json.loads(records[-1].read_text())
    status = data["status"]
    pid = data.get("pid")
    if status == "running" and (
        data.get("boot_id") != _boot_id() or not pid or data.get("process_start") != _process_start(pid)
    ):
        status = "stopped or runtime changed; rerun the original command to resume"
    print(f"Dataset: {data['dataset']}\nStatus: {status}\nPID: {pid or 'not recorded'}\nLog: {data['log']}")
    log = Path(data["log"])
    if args.tail and log.exists():
        print("\nRecent log:")
        with log.open(errors="replace") as source:
            print("".join(deque(source, maxlen=args.tail)), end="")
    return 0
