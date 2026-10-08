"""Giải N-Queens bằng IBM CP Optimizer."""

import os
from time import perf_counter

from docplex.cp.model import CpoModel
from docplex.cp.solution import SOLVE_STATUS_INFEASIBLE

from src.utils.validation import validate


def solve_nqueens(n: int) -> dict:
    """Tìm một nghiệm với một worker; timeout do runner quản lý."""
    if not isinstance(n, int) or isinstance(n, bool):
        raise TypeError("n phải là số nguyên")
    if n < 1:
        raise ValueError("n phải >= 1")

    started = perf_counter()

    model = CpoModel(name="nqueens")
    queens = model.integer_var_list(
        n, min=0, max=n - 1, name="q"
    )

    model.add(model.all_diff(queens))
    model.add(model.all_diff([queens[r] + r for r in range(n)]))
    model.add(model.all_diff([queens[r] - r for r in range(n)]))

    options = {
        "Workers": 1,
        "LogVerbosity": "Quiet",
    }

    # Có thể chỉ định đường dẫn cpoptimizer.exe qua biến môi trường.
    executable = os.environ.get("CPO_EXECUTABLE")
    if executable:
        options["execfile"] = executable

    build_s = perf_counter() - started

    solve_started = perf_counter()
    solution = model.solve(**options)
    solve_s = perf_counter() - solve_started

    native_status = solution.get_solve_status()
    q = None

    if solution.is_solution():
        q = [solution.get_value(queen) for queen in queens]

        if len(q) != n or not validate(q):
            raise RuntimeError(
                "CP Optimizer trả về bàn cờ không hợp lệ"
            )

        status = "SAT"
    elif native_status == SOLVE_STATUS_INFEASIBLE:
        status = "UNSAT"
    else:
        status = "UNKNOWN"

    return {
        "n": n,
        "encoding": None,
        "solver": "cplex_cp",
        "status": status,
        "native_status": native_status,
        "stop_cause": solution.get_stop_cause(),
        "q": q,
        "valid": True if q is not None else None,
        "build_s": build_s,
        "solve_s": solve_s,
        "total_wall_s": perf_counter() - started,
        "native_variables": n,
        "native_constraints": 3,
        "threads": 1,
    }