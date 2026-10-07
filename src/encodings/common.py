"""Các hàm chung để mã hóa N-Queens thành CNF."""


def cell_var(n: int, row: int, col: int) -> int:
    """ID biến ô (row, col), với hàng/cột hợp lệ từ 0 đến n-1."""
    return 1 + row * n + col


def new_aux_vars(
    top_id: int,
    count: int,
) -> tuple[list[int], int]:
    """Cấp count biến phụ, trả về (các ID mới, ID lớn nhất)."""
    if count < 0:
        raise ValueError("Số biến phụ phải >= 0")

    variables = list(range(top_id + 1, top_id + count + 1))
    return variables, top_id + count


def make_groups(n: int) -> dict[str, list[list[int]]]:
    """Tạo nhóm hàng, cột và đường chéo."""
    if not isinstance(n, int) or isinstance(n, bool):
        raise TypeError("n phải là số nguyên")

    if n < 1:
        raise ValueError("n phải >= 1")

    rows = [[] for _ in range(n)]
    columns = [[] for _ in range(n)]
    diagonal_minus = [[] for _ in range(2 * n - 1)]
    diagonal_plus = [[] for _ in range(2 * n - 1)]

    for row in range(n):
        for col in range(n):
            variable = cell_var(n, row, col)

            rows[row].append(variable)
            columns[col].append(variable)

            diagonal_minus[row - col + n - 1].append(variable)
            diagonal_plus[row + col].append(variable)

    diagonals = [
        group
        for group in diagonal_minus + diagonal_plus
        if len(group) > 1
    ]

    return {
        "rows": rows,
        "columns": columns,
        "diagonals": diagonals,
    }


def build_cnf(n: int, encode_amo) -> tuple[list[list[int]], int]:
    """Ghép CNF N-Queens bằng hàm AMO được truyền vào.

    encode_amo(variables, top_id) phải trả về:
        (các clause AMO, ID lớn nhất sau khi cấp biến phụ)
    """
    groups = make_groups(n)

    rows = groups["rows"]
    columns = groups["columns"]
    diagonals = groups["diagonals"]

    top_id = n * n
    clauses = []

    # ALO: ít nhất một hậu trên mỗi hàng và mỗi cột.
    for group in rows + columns:
        clauses.append(group.copy())

    # AMO: nhiều nhất một hậu trên mỗi hàng, cột, đường chéo.
    for group in rows + columns + diagonals:
        if len(group) > 1:
            amo_clauses, top_id = encode_amo(group, top_id)
            clauses.extend(amo_clauses)

    return clauses, top_id