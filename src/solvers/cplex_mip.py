"""Giải N-Queens bằng IBM CPLEX MIP."""

from time import perf_counter

from docplex.mp.model import Model

from src.encodings.common import cell_var, make_groups
from src.utils.validation import validate


def solve_nqueens(n: int) -> dict:
    """Tìm một nghiệm với một thread; timeout do runner quản lý."""
    started = perf_counter()

    # make_groups() đồng thời kiểm tra n hợp lệ.
    groups = make_groups(n)

    with Model(name="nqueens") as model:
        model.parameters.threads = 1

        # Mỗi ID ô ánh xạ đến một biến nhị phân của CPLEX.
        x = model.binary_var_dict(
            range(1, n * n + 1),
            name="x",
        )

        # Mỗi hàng và mỗi cột có đúng một hậu.
        for group in groups["rows"] + groups["columns"]:
            model.add_constraint(
                model.sum(x[v] for v in group) == 1
            )

        # Mỗi đường chéo có nhiều nhất một hậu.
        for group in groups["diagonals"]:
            model.add_constraint(
                model.sum(x[v] for v in group) <= 1
            )

        model.minimize(0)
        build_s = perf_counter() - started

        solve_started = perf_counter()
        solution = model.solve(log_output=False)
        solve_s = perf_counter() - solve_started

        details = model.solve_details
        q = None

        if solution is not None:
            q = []

            for row in range(n):
                columns = [
                    col for col in range(n)
                    if solution.get_value(
                        x[cell_var(n, row, col)]
                    ) > 0.5
                ]

                if len(columns) != 1:
                    raise RuntimeError(
                        f"Hàng {row} không có đúng một hậu"
                    )

                q.append(columns[0])

            if not validate(q):
                raise RuntimeError(
                    "CPLEX MIP trả về bàn cờ không hợp lệ"
                )

            status = "SAT"
        elif details.status_code == 103:
            status = "UNSAT"
        elif details.status_code == 1016:
            status = "LICENSE_ERROR"
        else:
            status = "UNKNOWN"

        result = {
            "n": n,
            "encoding": None,
            "solver": "cplex_mip",
            "status": status,
            "native_status": details.status,
            "native_status_code": details.status_code,
            "q": q,
            "valid": True if q is not None else None,
            "build_s": build_s,
            "solve_s": solve_s,
            "native_variables": model.number_of_variables,
            "native_constraints": model.number_of_constraints,
            "threads": 1,
        }

    result["total_wall_s"] = perf_counter() - started
    return result