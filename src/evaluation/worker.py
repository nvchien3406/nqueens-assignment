"""Chạy một cấu hình solver trong tiến trình riêng và lưu kết quả."""

import argparse
import importlib
import json
import sys
from pathlib import Path
from uuid import uuid4

from src.utils.resource_monitor import run_process
from src.utils.validation import validate


ROOT = Path(__file__).resolve().parents[2]

ENCODINGS = (
    "binomial",
    "binary",
    "commander",
    "product",
    "sequential",
)
SAT_SOLVERS = ("glucose3", "cadical195")
BASELINES = ("cp_sat", "gurobi_mip", "cplex_cp", "cplex_mip")

METHODS = tuple(
    f"{solver}:{encoding}"
    for solver in SAT_SOLVERS
    for encoding in ENCODINGS
) + BASELINES


def classify_error(error):
    """Phân loại các lỗi nhận diện được; còn lại giữ là ERROR."""
    if isinstance(error, MemoryError):
        return "MEMORY_LIMIT"

    if isinstance(error, (ImportError, FileNotFoundError)):
        return "INSTALL_ERROR"

    message = str(error).lower()
    if any(word in message for word in (
        "license", "licence", "size-limited", "promotional version",
    )):
        return "LICENSE_ERROR"

    return "ERROR"


def solve_case(n, method):
    """Chỉ import solver được chọn, rồi xác thực kết quả."""
    if ":" in method:
        solver, encoding = method.split(":")
        module = importlib.import_module("src.solvers.sat_solvers")
        result = module.solve_nqueens(n, encoding, solver)
    else:
        module = importlib.import_module(f"src.solvers.{method}")
        result = module.solve_nqueens(n)

    if result["status"] == "SAT":
        q = result.get("q")

        if not isinstance(q, list) or len(q) != n or not validate(q):
            result.update(status="INVALID_MODEL", valid=False)
        else:
            result["valid"] = True

    return result


def run_case(
    n,
    method,
    output_dir="results/runs",
    wall_limit_s=30,
    memory_limit_mib=8192,
):
    """Được gọi tuần tự bởi correctness hoặc main_experiment."""
    if not isinstance(n, int) or isinstance(n, bool) or n < 1:
        raise ValueError("n phải là số nguyên dương")

    if method not in METHODS:
        raise ValueError(f"Cấu hình không được hỗ trợ: {method}")

    run_id = uuid4().hex
    run_dir = Path(output_dir).resolve() / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    child_path = run_dir / "solver.json"
    log_path = run_dir / "solver.log"

    command = [
        sys.executable, "-B", "-m", "src.evaluation.worker",
        "--n", str(n),
        "--method", method,
        "--output", str(child_path),
    ]

    metrics = run_process(
        command,
        ROOT,
        log_path,
        wall_limit_s,
        memory_limit_mib,
    )

    limit_status = metrics.pop("limit_status")
    result = {"status": "ERROR", "q": None, "valid": None}

    if limit_status:
        result["status"] = limit_status
    elif metrics["exit_code"] != 0:
        result["error"] = "Tiến trình lỗi; xem solver.log"
    elif not child_path.exists():
        result["error"] = "Tiến trình không tạo solver.json"
    else:
        try:
            result = json.loads(
                child_path.read_text(encoding="utf-8")
            )
        except (OSError, ValueError) as error:
            result["error"] = str(error)

    # Giữ thời gian trong hàm solver dưới tên riêng.
    result["solver_call_wall_s"] = result.pop("total_wall_s", None)

    solver_name, _, encoding = method.partition(":")
    result.update(
        run_id=run_id,
        n=n,
        method=method,
        solver=solver_name,
        encoding=encoding or None,
        threads=1,
        wall_limit_s=wall_limit_s,
        memory_limit_mib=memory_limit_mib,
        log_path=str(log_path),
    )

    # total_wall_s ở đây đo toàn bộ tiến trình.
    result.update(metrics)

    (run_dir / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return result


def main():
    """Điểm vào của tiến trình con do run_case() tạo."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, required=True)
    parser.add_argument("--method", choices=METHODS, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        result = solve_case(args.n, args.method)
    except Exception as error:
        result = {
            "status": classify_error(error),
            "q": None,
            "valid": None,
            "error_type": type(error).__name__,
            "error": str(error),
        }

    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()