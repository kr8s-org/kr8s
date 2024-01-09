# SPDX-FileCopyrightText: Copyright (c) 2023-2024, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
import asyncio
from typing import List, Optional

import typer
from rich.console import Console

import kr8s
from kr8s.asyncio.objects import APIObject, object_from_name_type

console = Console()

# Missing Options
# TODO --allow-missing-template-keys
# TODO -f, --filename
# TODO --local
# TODO -o, --output
# TODO -R, --recursive
# TODO --show-managed-fields
# TODO --template


async def wait(
    resources: List[str] = typer.Argument(..., help="TYPE[.VERSION][.GROUP]"),
    all_namespaces: bool = typer.Option(
        False,
        "-A",
        "--all-namespaces",
        help="If present, list the requested object(s) across all namespaces. "
        "Namespace in current context is ignored even if specified with --namespace.",
    ),
    filename: str = typer.Option(
        "",
        "--filename",
        help="Filename, directory, or URL to files identifying the resource to wait on",
    ),
    all: bool = typer.Option(
        False,
        "--all",
        help="Select all resources in the namespace of the specified resource types",
    ),
    conditions: List[str] = typer.Option(
        [],
        "-f",
        "--for",
        help="The condition to wait on: "
        "[delete|condition=condition-name[=condition-value]|jsonpath='{JSONPath expression}'=JSONPath Condition]. "
        "The default condition-value is true.  Condition values are compared after Unicode simple case folding, "
        "which is a more general form of case-insensitivity.",
    ),
    label_selector: Optional[str] = typer.Option(
        None,
        "-l",
        "--selector",
        help="Selector (label query) to filter on, supports '=', '==', and '!='. "
        "(e.g. -l key1=value1,key2=value2). "
        "Matching objects must satisfy all of the specified label constraints.",
    ),
    field_selector: Optional[str] = typer.Option(
        None,
        "--field-selector",
        help="Selector (field query) to filter on, supports '=', '==', and '!='. "
        "The server only supports a limited number of field queries per type.",
    ),
    namespace: Optional[str] = typer.Option(
        None,
        "-n",
        "--namespace",
        help="If present, the namespace scope for this CLI request",
    ),
    timeout: Optional[str] = typer.Option(
        None,
        "--timeout",
        help="The length of time to wait before giving up.  Zero means check once and don't "
        "wait, negative means wait for a week.",
    ),
):
    """Wait for a specific condition on one or many resources.

    \b
    The command takes multiple resources and waits until the specified condition is
    seen in the Status field of every given resource.

    \b
    Alternatively, the command can wait for the given set of resources to be deleted
    by providing the "delete" keyword as the value to the --for flag.

    \b
    A successful message will be printed to stdout indicating when the specified
    condition has been met. You can use -o option to change to output destination.

    \b
    Examples:
    \b
        # Wait for the pod "busybox1" to contain the status condition of type "Ready"
        kubectl wait --for=condition=Ready pod/busybox1

    \b
        # The default value of status condition is true; you can wait for other targets after an equal delimiter
        # (compared after Unicode simple case folding, which is a more general form of case-insensitivity):
        kubectl wait --for=condition=Ready=false pod/busybox1

    \b
        # Wait for the pod "busybox1" to contain the status phase to be "Running".
        kubectl wait --for=jsonpath='{.status.phase}'=Running pod/busybox1

    \b
        # Wait for the pod "busybox1" to be deleted, with a timeout of 60s, after having issued the "delete" command
        kubectl delete pod/busybox1
        kubectl wait --for=delete pod/busybox1 --timeout=60s
    """
    api = await kr8s.asyncio.api()
    if all_namespaces:
        namespace = kr8s.ALL
    if timeout and "s" not in timeout:
        # TODO support more units
        console.print("error: --timeout must be a duration in seconds")
        raise typer.Exit(code=1)
    timeout = int(timeout[:-1]) if timeout else None
    if filename:
        console.print("error: --filename is not supported yet")
        raise typer.Exit(code=1)
    if not all:
        try:
            objects = await asyncio.gather(
                *[object_from_name_type(r, namespace=namespace) for r in resources]
            )
        except kr8s.NotFoundError as e:
            console.print("Error from server (NotFound): " + str(e))
            raise typer.Exit(code=1)
    else:
        assert len(resources) == 1
        objects = await api.get(
            resources[0],
            namespace=namespace,
            label_selector=label_selector,
            field_selector=field_selector,
        )

    async def wait_for(o: APIObject, conditions: List[str]):
        try:
            await o.wait(conditions=conditions, timeout=timeout)
        except asyncio.TimeoutError:
            console.print(
                f"error: timed out waiting for the condition on {o.singular}/{o.name}"
            )
            raise typer.Exit(code=1)
        console.print(f"{o.singular}/{o.name} condition met")

    await asyncio.gather(*[wait_for(o, conditions=conditions) for o in objects])
