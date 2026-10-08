"""Kiểm tra tính đúng tuần tự qua worker; không phải benchmark."""

import argparse
import json
import math
from pathlib import Path
from uuid import uuid4

from src.evaluation.worker import METHODS, ROOT, run_case
from src.utils.validation import validate


SIZES = (1, 2, 3, 4, 5, 6, 8)
CPLEX_METHODS = ("cplex_cp", "cplex_mip")


def positive_number(text):
    """Đọc giới hạn thời gian hoặc RAM từ dòng lệnh."""
    value = float(text)

    if not math.isfinite(value) or value <= 0:
        raise argparse.ArgumentTypeError(
            "Giá trị phải hữu hạn và > 0"
        )

    return value


def check_result(result, n):
    """Đối chiếu trạng thái; tự kiểm tra lại nghiệm SAT."""
    expected = "UNSAT" if n in (2, 3) else "SAT"

    if result.get("status") != expected:
        return False

    q = result.get("q")

    if expected == "UNSAT":
        return q is None

    return (
        isinstance(q, list)
        and len(q) == n
        and validate(q)
        and result.get("valid") is True
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument(
        "--include-cplex",
        action="store_true",
        help="Chạy thêm CPLEX CP và CPLEX MIP",
    )
    parser.add_argument(
        "--wall-limit",
        type=positive_number,
        default=30,
    )
    parser.add_argument(
        "--memory-mib",
        type=positive_number,
        default=8192,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "results" / "correctness",
    )

    args = parser.parse_args()

    # Mỗi lần kiểm tra có thư mục riêng, không ghi đè lần trước.
    output_dir = args.output_dir.resolve() / uuid4().hex
    output_dir.mkdir(parents=True, exist_ok=False)

    rows = []

    # Ghi ngay sau mỗi ca để giữ kết quả đã hoàn tất.
    with (output_dir / "checks.jsonl").open(
        "w", encoding="utf-8",
    ) as stream:
        for n in SIZES:
            for method in METHODS:
                expected = "UNSAT" if n in (2, 3) else "SAT"

                if method in CPLEX_METHODS and not args.include_cplex:
                    result = {
                        "n": n,
                        "method": method,
                        "status": "NOT_RUN",
                        "q": None,
                        "valid": None,
                        "check": "SKIP",
                        "reason": "Chưa chọn --include-cplex",
                    }
                else:
                    result = run_case(
                        n=n,
                        method=method,
                        output_dir=output_dir / "runs",
                        wall_limit_s=args.wall_limit,
                        memory_limit_mib=args.memory_mib,
                    )

                    result["check"] = (
                        "PASS"
                        if check_result(result, n)
                        else "FAIL"
                    )

                result["expected_status"] = expected
                rows.append(result)

                stream.write(
                    json.dumps(result, ensure_ascii=False) + "\n"
                )
                stream.flush()

                print(
                    f"{method:<24} n={n:>2} "
                    f"{result['status']:<16} {result['check']}",
                    flush=True,
                )

    passed = sum(row["check"] == "PASS" for row in rows)
    failed = sum(row["check"] == "FAIL" for row in rows)
    skipped = sum(row["check"] == "SKIP" for row in rows)

    report = {
        "kind": "correctness",
        "sizes": list(SIZES),
        "methods": list(METHODS),
        "include_cplex": args.include_cplex,
        "wall_limit_s": args.wall_limit,
        "memory_limit_mib": args.memory_mib,
        "planned": len(rows),
        "attempted": passed + failed,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "all_configurations_passed": failed == 0 and skipped == 0,
        "results": rows,
    }

    (output_dir / "summary.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Passed: {passed}/{passed + failed}")
    print(f"Failed: {failed}; Skipped: {skipped}")
    print(f"Saved: {output_dir}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())