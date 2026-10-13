from decimal import Decimal

import pytest

from app.services.scoring import calculate_net


@pytest.mark.parametrize(
    ("correct", "wrong", "expected"),
    [
        (20, 0, "20.00"),
        (15, 3, "14.00"),
        (10, 4, "8.67"),
        (10, 5, "8.33"),
        (0, 0, "0.00"),
        (0, 3, "-1.00"),
    ],
)
def test_calculate_net(correct, wrong, expected):
    assert calculate_net(correct, wrong) == Decimal(expected)
