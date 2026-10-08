#Kiểm tra nghiệm N-Queens, đề phòng trường hợp mã hóa thiếu ràng buộc
"""Kiểm tra nghiệm N-Queens độc lập với solver và encoder."""


def validate(q: list[int]) -> bool:
    """q[r] = c: hậu ở hàng r, cột c; bàn cờ có kích thước len(q)."""
    n = len(q)

    if n < 1:
        return False

    # Cột phải là số nguyên trong phạm vi bàn cờ.
    if any(
        not isinstance(c, int)
        or isinstance(c, bool)
        or not 0 <= c < n
        for c in q
    ):
        return False

    # Mỗi phần tử đã tương ứng với một hàng.
    # Kiểm tra các hậu không trùng cột.
    if len(set(q)) != n:
        return False

    # Các ô trên cùng đường chéo có cùng r - c hoặc r + c.
    if len({r - c for r, c in enumerate(q)}) != n:
        return False

    if len({r + c for r, c in enumerate(q)}) != n:
        return False

    return True