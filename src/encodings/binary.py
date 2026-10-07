"""Mã hóa AMO bằng binary/bitwise encoding."""

from src.encodings.common import new_aux_vars


def encode_amo(
    variables: list[int],
    top_id: int,
) -> tuple[list[list[int]], int]:
    """Mỗi biến gốc đúng sẽ buộc các bit phụ mang mã riêng của nó."""
    m = len(variables)

    if m <= 1:
        return [], top_id

    # Số bit cần để biểu diễn các chỉ số từ 0 đến m-1.
    bit_count = (m - 1).bit_length()

    bits, top_id = new_aux_vars(top_id, bit_count)
    clauses = []

    for index, variable in enumerate(variables):
        for bit_position, bit_variable in enumerate(bits):
            bit_value = (index >> bit_position) & 1

            if bit_value == 1:
                literal = bit_variable
            else:
                literal = -bit_variable

            # variable -> literal
            clauses.append([-variable, literal])

    return clauses, top_id