# SPDX-FileCopyrightText: Copyright (c) 2023-2024, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
from kubectl_ng._formatters import time_delta_to_string


def test_time_delta_to_string():
    from datetime import timedelta

    assert time_delta_to_string(timedelta(seconds=1), 1) == "Just Now"
    assert time_delta_to_string(timedelta(seconds=10), 1) == "10s"
    assert time_delta_to_string(timedelta(minutes=1, seconds=5), 1) == "1m"
    assert time_delta_to_string(timedelta(minutes=1, seconds=5), 1, " ago") == "1m ago"
    assert time_delta_to_string(timedelta(minutes=1, seconds=5), 2) == "1m5s"
    assert time_delta_to_string(timedelta(hours=1), 1) == "1h"
    assert time_delta_to_string(timedelta(hours=3), 1) == "3h"
    assert time_delta_to_string(timedelta(days=3, hours=4, minutes=2), 3) == "3d4h2m"
    assert time_delta_to_string(timedelta(days=3, hours=4, minutes=2), 2) == "3d4h"
    assert time_delta_to_string(timedelta(days=3, hours=0, minutes=2), 2) == "3d"
