from decimal import ROUND_HALF_UP, Decimal


def calculate_net(correct: int, wrong: int) -> Decimal:
    """LGS net score: every 3 wrong answers cancel 1 correct answer."""
    net = Decimal(correct) - Decimal(wrong) / 3
    return net.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
