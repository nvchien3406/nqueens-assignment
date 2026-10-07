"""Mã hóa AMO bằng binomial, còn gọi là pairwise."""


def encode_amo(
    variables: list[int],
    top_id: int,
) -> tuple[list[list[int]], int]:
    """Cấm mọi cặp biến cùng đúng; không cần biến phụ."""
    clauses = []
    m = len(variables)

    for i in range(m):
        for j in range(i + 1, m):
            clauses.append([-variables[i], -variables[j]])

    return clauses, top_id