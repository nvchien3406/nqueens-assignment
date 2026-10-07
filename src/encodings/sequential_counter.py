"""Mã hóa AMO bằng Sequential Counter."""

from src.encodings.common import new_aux_vars


def encode_amo(
    variables: list[int],
    top_id: int,
) -> tuple[list[list[int]], int]:
    """Trả về các clause AMO và ID biến lớn nhất sau mã hóa."""

    m = len(variables)

    if m <= 1:
        return [], top_id

    # Mỗi vị trí, trừ vị trí cuối, có một biến phụ.
    counters, top_id = new_aux_vars(top_id, m - 1)

    # Biến đầu đúng thì bật biến phụ đầu tiên.
    clauses = [[-variables[0], counters[0]]]

    for i in range(1, m - 1):
        # Biến hiện tại đúng thì bật biến phụ hiện tại.
        clauses.append([-variables[i], counters[i]])

        # Truyền tín hiệu đã có biến đúng từ phía trước.
        clauses.append([-counters[i - 1], counters[i]])

        # Không cho biến hiện tại đúng nếu tín hiệu trước đã bật.
        clauses.append([-variables[i], -counters[i - 1]])

    # Biến cuối không cần biến phụ mới, chỉ cần kiểm tra phía trước.
    clauses.append([-variables[-1], -counters[-1]])

    return clauses, top_id