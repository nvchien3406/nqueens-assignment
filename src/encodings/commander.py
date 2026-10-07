"""Mã hóa AMO bằng cách chia nhóm và dùng biến commander."""

from src.encodings.binomial import encode_amo as pairwise_amo
from src.encodings.common import new_aux_vars


GROUP_SIZE = 3


def encode_amo(
    variables: list[int],
    top_id: int,
) -> tuple[list[list[int]], int]:
    """Trả về các clause AMO và ID biến lớn nhất sau mã hóa."""

    # Nhóm nhỏ thì dùng pairwise trực tiếp.
    if len(variables) <= GROUP_SIZE:
        return pairwise_amo(variables, top_id)

    # Chia danh sách thành các nhóm tối đa 3 biến.
    groups = [
        variables[i:i + GROUP_SIZE]
        for i in range(0, len(variables), GROUP_SIZE)
    ]

    # Mỗi nhóm có một biến commander riêng.
    commanders, top_id = new_aux_vars(top_id, len(groups))
    clauses = []

    for group, commander in zip(groups, commanders):
        # Trong mỗi nhóm, nhiều nhất một biến được đúng.
        group_clauses, top_id = pairwise_amo(group, top_id)
        clauses.extend(group_clauses)

        # Một biến trong nhóm đúng thì commander phải đúng.
        for variable in group:
            clauses.append([-variable, commander])

        # Commander đúng thì ít nhất một biến trong nhóm phải đúng.
        clauses.append([-commander] + group)

    # Giữa các nhóm, nhiều nhất một commander được đúng.
    commander_clauses, top_id = encode_amo(commanders, top_id)
    clauses.extend(commander_clauses)

    return clauses, top_id