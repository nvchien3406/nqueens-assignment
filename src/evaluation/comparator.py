"""Tổng hợp kết quả đã lưu; không chạy solver."""

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median, quantiles

from src.main_experiment import load_config
from src.utils.validation import validate


METRICS = (
    "build_s",
    "solve_s",
    "build_solve_s",
    "solver_call_wall_s",
    "total_wall_s",
    "peak_rss_mib",
)


def read_results(path):
    """Đọc từng bản ghi JSONL, báo lỗi nếu dữ liệu bị hỏng."""
    rows = []

    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue

            try:
                row = json.loads(line)
            except ValueError as error:
                raise ValueError(
                    f"JSON lỗi tại dòng {line_number} của {path}"
                ) from error

            if not isinstance(row, dict):
                raise ValueError(
                    f"Dòng {line_number} không phải bản ghi"
                )

            rows.append(row)

    return rows


def is_success(row):
    """Chỉ nhận trạng thái đúng và nghiệm đã được kiểm tra."""
    n = row["n"]

    if row["status"] == "UNSAT":
        return n in (2, 3) and row.get("q") is None

    q = row.get("q")

    return (
        row["status"] == "SAT"
        and row.get("valid") is True
        and isinstance(q, list)
        and len(q) == n
        and validate(q)
    )


def metric_value(row, name):
    """Đọc một số đo; None nghĩa là không có dữ liệu."""
    if name == "build_solve_s":
        build = metric_value(row, "build_s")
        solve = metric_value(row, "solve_s")

        return (
            None
            if build is None or solve is None
            else build + solve
        )

    value = row.get(name)

    if value is None:
        return None

    if (
        type(value) not in (int, float)
        or not math.isfinite(value)
        or value < 0
    ):
        raise ValueError(
            f"Giá trị không hợp lệ cho {name}: {value}"
        )

    return value


def summarize(rows, config):
    """Tổng hợp từng nhóm N/phương pháp theo kế hoạch đã lưu."""
    groups = defaultdict(list)
    seen = set()
    experiment_ids = set()

    for row in rows:
        n = row["n"]
        method = row["method"]
        repeat = row["repeat"]

        if (
            type(n) is not int
            or n not in config["sizes"]
            or method not in config["methods"]
            or type(repeat) is not int
            or not 1 <= repeat <= config["repeats"]
        ):
            raise ValueError(
                "Bản ghi không khớp cấu hình thí nghiệm"
            )

        if not isinstance(row.get("status"), str):
            raise ValueError("Bản ghi thiếu trạng thái")

        key = (n, method, repeat)

        if key in seen:
            raise ValueError(f"Trùng lượt chạy: {key}")

        seen.add(key)
        experiment_ids.add(row["experiment_id"])
        groups[n, method].append(row)

    if len(experiment_ids) > 1:
        raise ValueError(
            "Không gộp nhiều thí nghiệm trong một bảng"
        )

    summaries = []

    for n in config["sizes"]:
        for method in config["methods"]:
            group = groups[n, method]
            good = [
                row for row in group
                if is_success(row)
            ]
            statuses = Counter(
                row["status"] for row in group
            )
            not_run = statuses["NOT_RUN"]

            summary = {
                "n": n,
                "method": method,
                "planned": config["repeats"],
                "recorded": len(group),
                "missing": config["repeats"] - len(group),
                "solved": len(good),
                "failed": len(group) - len(good) - not_run,
                "not_run": not_run,
                "invalid_results": sum(
                    row["status"] in ("SAT", "UNSAT")
                    and not is_success(row)
                    for row in group
                ),
                "status_counts": dict(statuses),
            }

            for metric in METRICS:
                values = [
                    value
                    for row in good
                    if (
                        value := metric_value(row, metric)
                    ) is not None
                ]

                summary[f"{metric}_samples"] = len(values)
                summary[f"{metric}_median"] = (
                    median(values) if values else None
                )

                iqr = None
                if len(values) >= 2:
                    q1, _, q3 = quantiles(
                        values,
                        n=4,
                        method="inclusive",
                    )
                    iqr = q3 - q1

                summary[f"{metric}_iqr"] = iqr

            summaries.append(summary)

    return summaries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "experiment_dir",
        type=Path,
        help="Thư mục chứa config.json và results.jsonl",
    )
    args = parser.parse_args()

    directory = args.experiment_dir.resolve()

    config = load_config(directory / "config.json")
    rows = read_results(directory / "results.jsonl")
    summaries = summarize(rows, config)

    report = {
        "source": str(directory),
        "statistics_scope": (
            "Chỉ các lượt giải thành công và hợp lệ"
        ),
        "iqr_method": (
            "inclusive; ít hơn hai mẫu thì để null"
        ),
        "groups": summaries,
    }

    (directory / "analysis.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    with (directory / "analysis.csv").open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=list(summaries[0]),
        )
        writer.writeheader()

        for summary in summaries:
            csv_row = dict(summary)
            csv_row["status_counts"] = json.dumps(
                summary["status_counts"]
            )
            writer.writerow(csv_row)

    for summary in summaries:
        wall = summary["total_wall_s_median"]
        wall_text = "-" if wall is None else f"{wall:.4f}s"

        print(
            f"{summary['method']:<24} n={summary['n']:>5} "
            f"solved={summary['solved']}/{summary['planned']} "
            f"failed={summary['failed']} "
            f"not_run={summary['not_run']} "
            f"missing={summary['missing']} "
            f"median_wall={wall_text}"
        )

    print(f"Saved: {directory / 'analysis.csv'}")


if __name__ == "__main__":
    main()