# SPDX-FileCopyrightText: Copyright (c) 2023-2024, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
import time

from kr8s.objects import Pod


def test_gen_pod(ns):
    pod = Pod.gen(
        name="foo",
        namespace=ns,
        image="nginx",
        labels={"app": "foo"},
        annotations={"bar": "baz"},
    )
    assert isinstance(pod, Pod)
    assert pod.name == "foo"
    assert pod.namespace == ns
    assert pod.spec.containers[0].image == "nginx"
    assert "app" in pod.labels
    assert "bar" in pod.annotations
    pod.create()
    while not pod.exists():
        time.sleep(1)
    pod.delete()


def test_gen_simple_pod(ns):
    pod = Pod.gen(name="foo", image="nginx")  # Minimum arguments you can pass
    pod.namespace = ns  # We need to set the namespace to avoid collisions in tests
    pod.create()
    while not pod.exists():
        time.sleep(1)
    pod.delete()
