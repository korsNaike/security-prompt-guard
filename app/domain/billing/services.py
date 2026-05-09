from math import ceil


def calculate_discounted_cost(*, base_cost: int, discount_percent: int) -> int:
    if base_cost <= 0:
        raise ValueError("base_cost must be positive")
    if discount_percent < 0 or discount_percent > 100:
        raise ValueError("discount_percent must be between 0 and 100")
    return ceil(base_cost * (1 - discount_percent / 100))
