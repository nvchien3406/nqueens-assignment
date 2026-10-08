"""Điều phối thí nghiệm tuần tự, lưu cấu hình, môi trường và kết quả."""

import argparse
import csv
import hashlib
import json
import math
import platform
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from importlib.metadata import distributions
from pathlib import Path
from uuid import uuid4

import psutil

from src.evaluation.worker import METHODS, ROOT, run_case


CSV_FIELDS = (
    "experiment_id", "run_id", "n", "method", "repeat",
    "solver", "encoding", "status", "valid",
    "build_s", "solve_s", "solver_call_wall_s", "total_wall_s",
    "peak_rss_mib", "memory_sample_s", "base_variables", "aux_variables",
    "max_variable_id", "cnf_clauses", "native_variables",
    "native_constraints", "native_status", "native_status_code",
    "threads", "wall_limit_s", "memory_limit_mib",
    "exit_code", "error_type", "error", "reason", "log_path",
)


def write_json(path, data):
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_config(path):
    """Đọc và kiểm tra cấu hình trước khi tạo lượt chạy."""
    config = json.loads(path.read_text(encoding="utf-8-sig"))

    required = {
        "sizes", "repeats", "wall_limit_s", "memory_limit_mib",
        "methods", "disabled_methods",
    }
    if not isinstance(config, dict) or set(config) != required:
        raise ValueError(
            f"Cấu hình phải có đúng các mục: {sorted(required)}"
        )

    sizes = config["sizes"]
    if (
        not isinstance(sizes, list) or not sizes
        or any(type(n) is not int or n < 1 for n in sizes)
        or len(sizes) != len(set(sizes))
    ):
        raise ValueError(
            "sizes phải là danh sách số nguyên dương, không trùng"
        )

    repeats = config["repeats"]
    if type(repeats) is not int or repeats < 1:
        raise ValueError("repeats phải là số nguyên dương")

    for key in ("wall_limit_s", "memory_limit_mib"):
        value = config[key]
        if (
            type(value) not in (int, float)
            or not math.isfinite(value)
            or value <= 0
        ):
            raise ValueError(f"{key} phải hữu hạn và > 0")

    methods = config["methods"]
    if (
        not isinstance(methods, list) or not methods
        or any(method not in METHODS for method in methods)
        or len(methods) != len(set(methods))
    ):
        raise ValueError(
            "methods chứa cấu hình không hợp lệ hoặc bị trùng"
        )

    disabled = config["disabled_methods"]
    if (
        not isinstance(disabled, dict)
        or any(method not in methods for method in disabled)
        or any(
            not isinstance(reason, str) or not reason.strip()
            for reason in disabled.values()
        )
    ):
        raise ValueError(
            "disabled_methods phải ánh xạ cấu hình sang lý do bỏ qua"
        )

    if all(method in disabled for method in methods):
        raise ValueError("Cần ít nhất một cấu hình được bật")

    return config


def git_output(*arguments):
    """Đọc thông tin Git; trả None nếu không lấy được."""
    try:
        return subprocess.check_output(
            ["git", *arguments],
            cwd=ROOT,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        ).strip()
    except (OSError, subprocess.SubprocessError):
        return None


def environment_info():
    """Ghi môi trường và dấu vết mã nguồn tại thời điểm bắt đầu."""
    git_status = git_output("status", "--porcelain")

    return {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "processor": platform.processor(),
        "hostname": platform.node(),
        "physical_cores": psutil.cpu_count(logical=False),
        "logical_cpus": psutil.cpu_count(logical=True),
        "ram_mib": psutil.virtual_memory().total / 1024**2,
        "commit_hash": git_output("rev-parse", "HEAD"),
        "git_dirty": None if git_status is None else bool(git_status),
        "package_versions": {
            package.metadata["Name"]: package.version
            for package in distributions()
            if package.metadata["Name"]
        },
        "source_sha256": {
            str(path.relative_to(ROOT)): hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            for path in sorted((ROOT / "src").rglob("*.py"))
        },
        "run_order": "repeat, size, methods theo thứ tự trong config",
        "solver_seed_policy": (
            "Dùng mặc định của solver; chưa đặt seed riêng"
        ),
        "resource_policy": (
            "Một lượt tại một thời điểm; RSS lấy mẫu mỗi 50 ms"
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "results" / "experiments",
    )
    args = parser.parse_args()

    config = load_config(args.config)

    # Thu thập trước khi tạo kết quả để giảm ảnh hưởng lên git_dirty.
    metadata = environment_info()

    experiment_id = (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + "_" + uuid4().hex[:8]
    )
    output_dir = args.output_dir.resolve() / experiment_id
    output_dir.mkdir(parents=True, exist_ok=False)

    write_json(output_dir / "config.json", config)
    write_json(output_dir / "environment.json", metadata)

    planned = (
        len(config["sizes"])
        * len(config["methods"])
        * config["repeats"]
    )
    counts = Counter()
    processed = 0
    state = "RUNNING"
    exit_code = 0

    print(f"Kết quả sẽ lưu tại: {output_dir}", flush=True)

    try:
        with (
            (output_dir / "results.jsonl").open(
                "w", encoding="utf-8"
            ) as raw,
            (output_dir / "results.csv").open(
                "w", encoding="utf-8-sig", newline=""
            ) as table,
        ):
            writer = csv.DictWriter(
                table,
                fieldnames=CSV_FIELDS,
                extrasaction="ignore",
            )
            writer.writeheader()

            for repeat in range(1, config["repeats"] + 1):
                for n in config["sizes"]:
                    for method in config["methods"]:
                        reason = config["disabled_methods"].get(method)

                        if reason is not None:
                            solver, _, encoding = method.partition(":")
                            result = {
                                "n": n,
                                "method": method,
                                "solver": solver,
                                "encoding": encoding or None,
                                "status": "NOT_RUN",
                                "q": None,
                                "valid": None,
                                "reason": reason,
                                "wall_limit_s": config["wall_limit_s"],
                                "memory_limit_mib": config["memory_limit_mib"],
                            }
                        else:
                            result = run_case(
                                n=n,
                                method=method,
                                output_dir=output_dir / "runs",
                                wall_limit_s=config["wall_limit_s"],
                                memory_limit_mib=config["memory_limit_mib"],
                            )

                        result.update(
                            experiment_id=experiment_id,
                            repeat=repeat,
                        )

                        # Lưu ngay sau mỗi lượt.
                        raw.write(
                            json.dumps(result, ensure_ascii=False) + "\n"
                        )
                        raw.flush()

                        writer.writerow(result)
                        table.flush()

                        processed += 1
                        counts[result["status"]] += 1

                        print(
                            f"[{processed}/{planned}] {method:<24} "
                            f"n={n:>5} rep={repeat} {result['status']}",
                            flush=True,
                        )

        state = "FINISHED"

    except KeyboardInterrupt:
        state = "INTERRUPTED"
        exit_code = 130
        print("Đã ngắt. Các kết quả hoàn tất được giữ lại.")

    except Exception:
        state = "ERROR"
        raise

    finally:
        write_json(output_dir / "summary.json", {
            "experiment_id": experiment_id,
            "state": state,
            "planned": planned,
            "processed": processed,
            "remaining": planned - processed,
            "status_counts": dict(counts),
        })

    print(f"Saved: {output_dir}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())