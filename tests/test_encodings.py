"""Kiểm tra các encoder AMO và CNF N-Queens."""

from itertools import product, combinations

import pytest
from pysat.solvers import Solver

from src.encodings.binomial import encode_amo as binomial_amo
from src.encodings.binary import encode_amo as binary_amo
from src.encodings.common import build_cnf
from src.utils.validation import validate
from src.encodings.commander import encode_amo as commander_amo
from src.encodings.product import encode_amo as product_amo
from src.encodings.sequential_counter import encode_amo as sequential_amo

ENCODERS = [
    pytest.param(binomial_amo, id="binomial"),
    pytest.param(binary_amo, id="binary"),
    pytest.param(commander_amo, id="commander"),
    pytest.param(product_amo, id="product"),
    pytest.param(sequential_amo, id="sequential"),
]


@pytest.mark.parametrize("encode_amo", ENCODERS)
@pytest.mark.parametrize("m", [*range(9), 10])
def test_amo(encode_amo, m):
    variables = list(range(1, m + 1))
    clauses, top_id = encode_amo(variables, m)

    assert top_id >= m
    assert all(
        0 < abs(literal) <= top_id
        for clause in clauses
        for literal in clause
    )

    with Solver(name="glucose3", bootstrap_with=clauses) as solver:
        for values in product([False, True], repeat=m):
            assumptions = [
                variable if value else -variable
                for variable, value in zip(variables, values)
            ]

            actual = solver.solve(assumptions=assumptions)
            expected = sum(values) <= 1

            assert actual == expected, (m, values)


@pytest.mark.parametrize("encode_amo", ENCODERS)
@pytest.mark.parametrize("solver_name", ["glucose3", "cadical195"])
@pytest.mark.parametrize("n", [1, 2, 3, 4, 5, 6, 8])
def test_nqueens(encode_amo, solver_name, n):
    clauses, top_id = build_cnf(n, encode_amo)

    assert top_id >= n * n

    with Solver(name=solver_name, bootstrap_with=clauses) as solver:
        satisfiable = solver.solve()

        assert satisfiable == (n not in (2, 3))

        if not satisfiable:
            return

        model = solver.get_model()
        assert model is not None

        true_variables = {
            literal for literal in model if literal > 0
        }

        q = []

        for row in range(n):
            columns = [
                col
                for col in range(n)
                if 1 + row * n + col in true_variables
            ]

            assert len(columns) == 1
            q.append(columns[0])

        assert validate(q)
@pytest.mark.parametrize("m", [17, 25, 100])
def test_product_recursive(m):
    # ID không liên tiếp để kiểm tra encoder không phụ thuộc cách đánh số.
    variables = [10 + 2 * i for i in range(m)]
    reserved_top = variables[-1] + 10

    clauses, top_id = product_amo(variables, reserved_top)

    assert top_id > reserved_top
    assert all(
        abs(literal) in variables
        or reserved_top < abs(literal) <= top_id
        for clause in clauses
        for literal in clause
    )

    with Solver(name="glucose3", bootstrap_with=clauses) as solver:
        # Không biến gốc nào đúng: phải SAT.
        assert solver.solve(
            assumptions=[-v for v in variables]
        )

        # Mỗi trường hợp có đúng một biến gốc đúng: phải SAT.
        for selected in variables:
            assumptions = [
                v if v == selected else -v
                for v in variables
            ]
            assert solver.solve(assumptions=assumptions)

        # Bất kỳ hai biến gốc cùng đúng: phải UNSAT.
        for first, second in combinations(variables, 2):
            assert not solver.solve(
                assumptions=[first, second]
            )