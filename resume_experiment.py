"""Tiếp tục thí nghiệm bị gián đoạn từ các bản ghi đã lưu."""

import csv
import json
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from src.main_experiment import (
    CSV_FIELDS,
    environment_info,
    load_config,
    write_json,
)
from src.evaluation.worker import run_case


EXPERIMENT = Path(
    r"E:\nqueens-assignment\results\experiments"
    r"\20261008T102037Z_10c488e7"
)


def main():
    config = load_config(EXPERIMENT / "config.json")
    raw_path = EXPERIMENT / "results.jsonl"
    csv_path = EXPERIMENT / "results.csv"

    # Dừng nếu dữ liệu có dòng hỏng; không tự ý bỏ dữ liệu.
    rows = []
    for line_number, line in enumerate(
        raw_path.read_text(encoding="utf-8").splitlines(), 1
    ):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as error:
            raise ValueError(
                f"results.jsonl bị hỏng tại dòng {line_number}"
            ) from error

    planned_cases = [
        (repeat, n, method)
        for repeat in range(1, config["repeats"] + 1)
        for n in config["sizes"]
        for method in config["methods"]
    ]
    planned_set = set(planned_cases)
    done = set()

    for row in rows:
        key = (row["repeat"], row["n"], row["method"])
        if key not in planned_set or key in done:
            raise ValueError(f"Bản ghi ngoài kế hoạch hoặc trùng: {key}")
        if row["experiment_id"] != EXPERIMENT.name:
            raise ValueError("experiment_id không khớp thư mục")
        done.add(key)

    # Không trộn kết quả từ các phiên bản thuật toán khác nhau.
    previous_environment = json.loads(
        (EXPERIMENT / "environment.json").read_text(encoding="utf-8")
    )
    current_environment = environment_info()

    for field in ("package_versions", "python_version"):
        if previous_environment.get(field) != current_environment.get(field):
            raise RuntimeError(
                f"{field} đã thay đổi. Dừng để kiểm tra."
            )

    old_sources = previous_environment["source_sha256"]
    new_sources = current_environment["source_sha256"]

    changed_files = sorted(
        name
        for name in old_sources.keys() | new_sources.keys()
        if old_sources.get(name) != new_sources.get(name)
    )

    allowed_changes = {"src/utils/resource_monitor.py"}
    unexpected_changes = [
        name
        for name in changed_files
        if name.replace("\\", "/") not in allowed_changes
    ]

    if unexpected_changes:
        raise RuntimeError(
            f"Có thay đổi mã nguồn chưa được kiểm tra: {unexpected_changes}"
        )

    current_environment["resume_note"] = (
        "Tiếp tục sau khi khởi động lại Windows; "
        "đã cấu hình thêm paging file tự quản lý trên ổ E; "
        "đã sửa phần dọn tiến trình trong resource_monitor.py; "
        "ba ca kiểm tra nhỏ đã PASS. "
        "Giữ giới hạn 100 giây và 8192 MiB."
    )
    current_environment["changed_source_files"] = changed_files
    current_environment["previous_records"] = len(rows)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    backup = EXPERIMENT / "resume_backups" / stamp
    backup.mkdir(parents=True, exist_ok=False)

    for name in ("results.jsonl", "results.csv", "summary.json"):
        source = EXPERIMENT / name
        if source.exists():
            shutil.copy2(source, backup / name)

    write_json(backup / "resume_environment.json", current_environment)

    # Chuẩn hóa xuống dòng cuối và dựng lại CSV từ JSONL đã kiểm tra.
    with raw_path.open("w", encoding="utf-8") as raw:
        for row in rows:
            raw.write(json.dumps(row, ensure_ascii=False) + "\n")

    with csv_path.open("w", encoding="utf-8-sig", newline="") as table:
        writer = csv.DictWriter(
            table, fieldnames=CSV_FIELDS, extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(rows)

    counts = Counter(row["status"] for row in rows)
    processed = len(rows)
    planned = len(planned_cases)
    state = "RUNNING"

    def save_summary():
        write_json(EXPERIMENT / "summary.json", {
            "experiment_id": EXPERIMENT.name,
            "state": state,
            "planned": planned,
            "processed": processed,
            "remaining": planned - processed,
            "status_counts": dict(counts),
        })

    print(f"Đã lưu: {processed}/{planned}", flush=True)
    print(f"Còn lại: {planned - processed}", flush=True)
    print(f"Bản sao dự phòng: {backup}", flush=True)
    save_summary()

    try:
        with (
            raw_path.open("a", encoding="utf-8") as raw,
            csv_path.open("a", encoding="utf-8", newline="") as table,
        ):
            writer = csv.DictWriter(
                table, fieldnames=CSV_FIELDS, extrasaction="ignore"
            )

            for repeat, n, method in planned_cases:
                if (repeat, n, method) in done:
                    continue

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
                    }
                else:
                    result = run_case(
                        n=n,
                        method=method,
                        output_dir=EXPERIMENT / "runs",
                        wall_limit_s=config["wall_limit_s"],
                        memory_limit_mib=config["memory_limit_mib"],
                    )

                result.update(
                    experiment_id=EXPERIMENT.name,
                    repeat=repeat,
                    resume_session=stamp,
                )

                raw.write(json.dumps(result, ensure_ascii=False) + "\n")
                raw.flush()
                writer.writerow(result)
                table.flush()

                processed += 1
                counts[result["status"]] += 1
                save_summary()

                print(
                    f"[{processed}/{planned}] {method:<24} "
                    f"n={n:>5} rep={repeat} {result['status']}",
                    flush=True,
                )

        state = "FINISHED"
    except KeyboardInterrupt:
        state = "INTERRUPTED"
        print("\nĐã dừng; giữ lại các lượt đã lưu.", flush=True)
    except Exception:
        state = "ERROR"
        raise
    finally:
        save_summary()


if __name__ == "__main__":
    main()