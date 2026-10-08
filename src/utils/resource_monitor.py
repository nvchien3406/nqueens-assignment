"""Chạy một tiến trình, giám sát thời gian và RSS của cây tiến trình."""

import math
import os
import subprocess
from time import perf_counter, sleep

import psutil


def stop_tree(root, known):
    """Dừng tiến trình gốc và các tiến trình con đã tìm thấy."""
    targets = {p.pid: p for p in known}

    if root is not None:
        try:
            # Tạm dừng tiến trình gốc trước khi thu thập các con.
            root.suspend()
            targets[root.pid] = root

            for child in root.children(recursive=True):
                targets[child.pid] = child
        except psutil.NoSuchProcess:
            pass

    for process in reversed(list(targets.values())):
        try:
            process.kill()
        except psutil.NoSuchProcess:
            pass

    _, alive = psutil.wait_procs(
        list(targets.values()),
        timeout=3,
    )
    if alive:
        raise RuntimeError("Không dừng được toàn bộ tiến trình solver")


def run_process(command, cwd, log_path, wall_limit_s, memory_limit_mib):
    """RAM lấy mẫu mỗi 50 ms; các giới hạn phải hữu hạn và dương."""
    for value in (wall_limit_s, memory_limit_mib):
        if not math.isfinite(value) or value <= 0:
            raise ValueError("Giới hạn phải hữu hạn và lớn hơn 0")

    known = {}
    root = None
    peak_rss = 0
    limit_status = None

    with open(log_path, "w", encoding="utf-8") as log:
        started = perf_counter()

        process = subprocess.Popen(
            command,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            creationflags=(
                subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            ),
        )

        try:
            try:
                root = psutil.Process(process.pid)
                known[root.pid] = root
            except psutil.NoSuchProcess:
                pass

            while process.poll() is None:
                # Tìm thêm các tiến trình con, ví dụ CP Optimizer.
                if root is not None:
                    try:
                        for child in root.children(recursive=True):
                            known[child.pid] = child
                    except psutil.NoSuchProcess:
                        pass

                # Tổng RSS của các tiến trình còn sống.
                rss = 0
                for pid, item in list(known.items()):
                    try:
                        if item.is_running():
                            rss += item.memory_info().rss
                        else:
                            known.pop(pid, None)
                    except psutil.NoSuchProcess:
                        known.pop(pid, None)

                peak_rss = max(peak_rss, rss)

                if rss > memory_limit_mib * 1024**2:
                    limit_status = "MEMORY_LIMIT"
                    break

                if perf_counter() - started >= wall_limit_s:
                    limit_status = "TIMEOUT"
                    break

                sleep(0.05)
        finally:
            # Cũng dọn tiến trình khi người dùng nhấn Ctrl+C.
            stop_tree(root, known.values())

            if process.poll() is None:
                process.kill()

            process.wait()

    return {
        "limit_status": limit_status,
        "exit_code": process.returncode,
        "total_wall_s": perf_counter() - started,
        "peak_rss_mib": peak_rss / 1024**2,
        "memory_sample_s": 0.05,
    }