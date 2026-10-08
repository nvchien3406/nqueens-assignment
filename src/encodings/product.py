"""Mã hóa AMO bằng Product đệ quy, ngưỡng pairwise là 4."""

from math import isqrt

from src.encodings.binomial import encode_amo as pairwise_amo
from src.encodings.common import new_aux_vars


def encode_amo(
    variables: list[int],
    top_id: int,
) -> tuple[list[list[int]], int]:
    """Trả về các clause AMO và ID biến lớn nhất sau mã hóa."""
    m = len(variables)

    # Trường hợp cơ sở, bao gồm cả nhóm rỗng và nhóm một biến.
    if m <= 4:
        return pairwise_amo(variables, top_id)

    row_count = isqrt(m - 1) + 1
    col_count = (m + row_count - 1) // row_count

    row_vars, top_id = new_aux_vars(top_id, row_count)
    col_vars, top_id = new_aux_vars(top_id, col_count)

    clauses = []

    # Mỗi biến gốc đúng kéo theo hàng và cột tương ứng đúng.
    for index, variable in enumerate(variables):
        row, col = divmod(index, col_count)
        clauses.append([-variable, row_vars[row]])
        clauses.append([-variable, col_vars[col]])

    # Tiếp tục dùng Product cho hai nhóm biến phụ.
    row_clauses, top_id = encode_amo(row_vars, top_id)
    col_clauses, top_id = encode_amo(col_vars, top_id)

    clauses.extend(row_clauses)
    clauses.extend(col_clauses)

    return clauses, top_id