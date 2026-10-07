"""Mã hóa AMO bằng lưới Product hai chiều."""

from math import isqrt

from src.encodings.binomial import encode_amo as pairwise_amo
from src.encodings.common import new_aux_vars


def encode_amo(
    variables: list[int],
    top_id: int,
) -> tuple[list[list[int]], int]:
    """Trả về các clause AMO và ID biến lớn nhất sau mã hóa."""

    m = len(variables)

    if m <= 1:
        return [], top_id

    # Số hàng = ceil(sqrt(m)).
    row_count = isqrt(m - 1) + 1

    # Số cột = ceil(m / row_count).
    col_count = (m + row_count - 1) // row_count

    # Cấp biến phụ riêng cho hàng và cột của lưới.
    row_vars, top_id = new_aux_vars(top_id, row_count)
    col_vars, top_id = new_aux_vars(top_id, col_count)

    clauses = []

    for index, variable in enumerate(variables):
        row, col = divmod(index, col_count)

        # variable đúng thì hàng và cột tương ứng phải đúng.
        clauses.append([-variable, row_vars[row]])
        clauses.append([-variable, col_vars[col]])

    # Nhiều nhất một hàng và một cột được chọn.
    row_clauses, top_id = pairwise_amo(row_vars, top_id)
    col_clauses, top_id = pairwise_amo(col_vars, top_id)

    clauses.extend(row_clauses)
    clauses.extend(col_clauses)

    return clauses, top_id