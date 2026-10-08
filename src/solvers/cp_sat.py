"""Giải N-Queens bằng OR-Tools CP-SAT."""

from time import perf_counter

from ortools.sat.python import cp_model

from src.utils.validation import validate


def solve_nqueens(n: int) -> dict:
    """Tìm một nghiệm với một worker; chưa áp dụng timeout."""
    if not isinstance(n, int) or isinstance(n, bool):
        raise TypeError("n phải là số nguyên")
    if n < 1:
        raise ValueError("n phải >= 1")

    started = perf_counter()
    model = cp_model.CpModel()

    # queens[row] là cột đặt hậu ở hàng row.
    queens = [
        model.new_int_var(0, n - 1, f"q_{row}")
        for row in range(n)
    ]

    # Không trùng cột hoặc đường chéo.
    model.add_all_different(queens)
    model.add_all_different([queens[row] + row for row in range(n)])
    model.add_all_different([queens[row] - row for row in range(n)])

    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    build_s = perf_counter() - started

    solve_started = perf_counter()
    native_status = solver.solve(model)
    solve_s = perf_counter() - solve_started

    q = None
    if native_status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        q = [solver.value(queen) for queen in queens]

        if len(q) != n or not validate(q):
            raise RuntimeError("CP-SAT trả về bàn cờ không hợp lệ")

        status = "SAT"
    elif native_status == cp_model.INFEASIBLE:
        status = "UNSAT"
    elif native_status == cp_model.MODEL_INVALID:
        raise RuntimeError(f"Mô hình CP-SAT không hợp lệ: {model.validate()}")
    else:
        status = "UNKNOWN"

    return {
        "n": n,
        "encoding": None,
        "solver": "cp_sat",
        "status": status,
        "native_status": solver.status_name(native_status),
        "q": q,
        "valid": True if q is not None else None,
        "build_s": build_s,
        "solve_s": solve_s,
        "total_wall_s": perf_counter() - started,
        "native_variables": len(model.proto.variables),
        "native_constraints": len(model.proto.constraints),
        "threads": 1,
    }