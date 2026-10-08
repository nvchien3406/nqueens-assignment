"""Giải N-Queens bằng mô hình MIP trên Gurobi."""

from time import perf_counter

import gurobipy as gp
from gurobipy import GRB

from src.utils.validation import validate


def solve_nqueens(n: int) -> dict:
    """Tìm một nghiệm với một thread; chưa áp dụng timeout."""
    if not isinstance(n, int) or isinstance(n, bool):
        raise TypeError("n phải là số nguyên")
    if n < 1:
        raise ValueError("n phải >= 1")

    started = perf_counter()

    with gp.Env(empty=True) as env:
        env.setParam("OutputFlag", 0)
        env.start()

        with gp.Model("nqueens", env=env) as model:
            model.Params.Threads = 1

            x = model.addVars(n, n, vtype=GRB.BINARY, name="x")

            # Mỗi hàng có đúng một hậu.
            for row in range(n):
                model.addConstr(
                    gp.quicksum(x[row, col] for col in range(n)) == 1
                )

            # Mỗi cột có đúng một hậu.
            for col in range(n):
                model.addConstr(
                    gp.quicksum(x[row, col] for row in range(n)) == 1
                )

            # Đường chéo có cùng row - col.
            for difference in range(1 - n, n):
                diagonal = [
                    x[row, row - difference]
                    for row in range(n)
                    if 0 <= row - difference < n
                ]
                if len(diagonal) > 1:
                    model.addConstr(gp.quicksum(diagonal) <= 1)

            # Đường chéo có cùng row + col.
            for total in range(2 * n - 1):
                diagonal = [
                    x[row, total - row]
                    for row in range(n)
                    if 0 <= total - row < n
                ]
                if len(diagonal) > 1:
                    model.addConstr(gp.quicksum(diagonal) <= 1)

            # Chỉ cần tìm nghiệm khả thi.
            model.setObjective(0, GRB.MINIMIZE)
            model.update()
            build_s = perf_counter() - started

            solve_started = perf_counter()
            model.optimize()
            solve_s = perf_counter() - solve_started

            native_status = model.Status
            q = None

            if model.SolCount > 0:
                q = []

                for row in range(n):
                    columns = [
                        col for col in range(n)
                        if x[row, col].X > 0.5
                    ]
                    if len(columns) != 1:
                        raise RuntimeError(
                            f"Hàng {row} không có đúng một hậu"
                        )
                    q.append(columns[0])

                if not validate(q):
                    raise RuntimeError(
                        "Gurobi trả về bàn cờ không hợp lệ"
                    )

                status = "SAT"
            elif native_status == GRB.INFEASIBLE:
                status = "UNSAT"
            else:
                status = "UNKNOWN"

            result = {
                "n": n,
                "encoding": None,
                "solver": "gurobi_mip",
                "status": status,
                "native_status": native_status,
                "q": q,
                "valid": True if q is not None else None,
                "build_s": build_s,
                "solve_s": solve_s,
                "native_variables": model.NumVars,
                "native_constraints": model.NumConstrs,
                "threads": 1,
            }

    result["total_wall_s"] = perf_counter() - started
    return result