from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction


def calculate_net(correct: int, wrong: int) -> Decimal:
    """LGS net score: every 3 wrong answers cancel 1 correct answer."""
    net = Decimal(correct) - Decimal(wrong) / 3
    return net.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def exact_net(correct: int, wrong: int) -> Fraction:
    """Unrounded net. Add or subtract these, then round once, so totals do not drift by 0.01."""
    return Fraction(correct) - Fraction(wrong, 3)


def round_net(net: Fraction) -> float:
    return float(round(net, 2))
