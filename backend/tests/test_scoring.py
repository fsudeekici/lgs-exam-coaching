from decimal import Decimal

import pytest

from app.services.scoring import calculate_net, exact_net, round_net


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


def test_rounding_once_avoids_drift():
    nets = [exact_net(5, 1)] * 6

    assert round_net(nets[0]) == 4.67
    assert round_net(sum(nets)) == 28.0
