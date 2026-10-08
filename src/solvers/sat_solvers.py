"""Giải N-Queens bằng encoder tự viết và SAT solver của PySAT."""

from time import perf_counter

from pysat.solvers import Solver

from src.encodings import (
    binary, binomial, commander, product, sequential_counter,
)
from src.encodings.common import build_cnf, cell_var
from src.utils.validation import validate


ENCODERS = {
    "binomial": binomial.encode_amo,
    "binary": binary.encode_amo,
    "commander": commander.encode_amo,
    "product": product.encode_amo,
    "sequential": sequential_counter.encode_amo,
}

SOLVERS = ("glucose3", "cadical195")


def decode_model(n: int, model: list[int]) -> list[int]:
    """Lấy các biến ô đúng trong model và chuyển thành q[r] = c."""
    true_cells = {lit for lit in model if 1 <= lit <= n * n}
    q = []

    for row in range(n):
        columns = [
            col for col in range(n)
            if cell_var(n, row, col) in true_cells
        ]
        if len(columns) != 1:
            raise RuntimeError(f"Hàng {row} không có đúng một hậu")
        q.append(columns[0])

    if not validate(q):
        raise RuntimeError("Solver trả về bàn cờ không hợp lệ")

    return q


def solve_nqueens(
    n: int,
    encoding: str = "sequential",
    solver_name: str = "glucose3",
) -> dict:
    """Dựng CNF, giải và kiểm tra nghiệm; chưa áp dụng timeout."""
    if encoding not in ENCODERS:
        raise ValueError(f"Encoding không được hỗ trợ: {encoding}")
    if solver_name not in SOLVERS:
        raise ValueError(f"Solver không được hỗ trợ: {solver_name}")

    started = perf_counter()
    clauses, top_id = build_cnf(n, ENCODERS[encoding])

    with Solver(name=solver_name, bootstrap_with=clauses) as solver:
        build_s = perf_counter() - started

        solve_started = perf_counter()
        satisfiable = solver.solve()
        solve_s = perf_counter() - solve_started

        q = None
        if satisfiable is True:
            model = solver.get_model()
            if model is None:
                raise RuntimeError("Solver báo SAT nhưng không trả model")
            q = decode_model(n, model)
            status = "SAT"
        elif satisfiable is False:
            status = "UNSAT"
        else:
            raise RuntimeError("Solver chưa xác định được SAT hay UNSAT")

    return {
        "n": n,
        "encoding": encoding,
        "solver": solver_name,
        "status": status,
        "q": q,
        "valid": True if q is not None else None,
        "build_s": build_s,
        "solve_s": solve_s,
        "total_wall_s": perf_counter() - started,
        "base_variables": n * n,
        "aux_variables": top_id - n * n,
        "max_variable_id": top_id,
        "cnf_clauses": len(clauses),
    }