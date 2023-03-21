# SPDX-FileCopyrightText: Copyright (c) 2023, Dask Developers, Yuvi Panda, Anaconda Inc, NVIDIA
# SPDX-License-Identifier: BSD 3-Clause License
import typer
from typing import List
from datetime import datetime

from rich.console import Console
from rich.table import Table
from rich import box

import kr8s
from kr8s import KubeConfig, HTTPClient
from kr8s.objects import Pod

from ._formatters import time_delta_to_string

TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

console = Console()


async def get(
    resources: List[str] = typer.Argument(..., help="TYPE[.VERSION][.GROUP]"),
    all_namespaces: bool = typer.Option(
        False,
        "-A",
        "--all-namespaces",
        help="If present, list the requested object(s) across all namespaces. "
        "Namespace in current context is ignored even if specified with --namespace.",
    ),
    namespace: str = typer.Option(
        None,
        "-n",
        "--namespace",
    ),
    selector: str = typer.Option(
        "",
        "-l",
        "--selector",
        help="Selector (label query) to filter on, supports '=', '==', and '!='.(e.g. -l key1=value1,key2=value2). "
        "Matching objects must satisfy all of the specified label constraints.",
    ),
    field_selector: str = typer.Option(
        "",
        "--field-selector",
        help="Selector (field query) to filter on, supports '=', '==', and '!='. "
        "(e.g. --field-selector key1=value1,key2=value2). The server only supports a limited number of field queries per type. ",
    ),
    show_kind: bool = typer.Option(
        False,
        "--show-kind",
        help="If present, list the resource type for the requested object(s).",
    ),
    show_labels: bool = typer.Option(
        False,
        "--show-labels",
        help="When printing, show all labels as the last column (default hide labels column).",
    ),
    label_columns: List[str] = typer.Option(
        [],
        "-L",
        "--label-columns",
        help="Accepts a comma separated list of labels that are going to be presented as columns. Names are case-sensitive. "
        "You can also use multiple flag options like -L label1 -L label2...",
    ),
):
    """Display one or many resources.

    Prints a table of the most important information about the specified resources. You can filter the list using a label
    selector and the --selector flag. If the desired resource type is namespaced you will only see results in your current
    namespace unless you pass --all-namespaces.

    By specifying the output as 'template' and providing a Jinja2 template as the value of the --template flag, you can filter
    the attributes of the fetched resources.

    Use "kubectl api-resources" for a complete list of supported resources.
    """
    resources = resources[1:]
    api = HTTPClient(KubeConfig.from_env())
    if not namespace:
        try:
            namespace = api.config.contexts[api.config.current_context]["namespace"]
        except KeyError:
            namespace = "default"
    if all_namespaces:
        namespace = kr8s.all
    if "pods" in resources or "pod" in resources:
        query = Pod.objects(api, namespace=namespace)
        if selector:
            query = query.filter(selector=selector)
        if field_selector:
            query = query.filter(field_selector=field_selector)
        pods = [pod async for pod in query]

        if not pods:
            console.print(f"No resources found in {namespace} namespace.")
            return

        table = Table(box=box.SIMPLE)
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Ready")
        table.add_column("Status")
        table.add_column("Restarts")
        table.add_column("Age")
        if show_labels:
            table.add_column("Labels")
        for column in label_columns:
            table.add_column(column)

        for pod in pods:
            name = f"pod/{pod.name}" if show_kind else pod.name
            n_containers = len(pod.obj["status"]["containerStatuses"])
            n_ready_containers = len(
                [s for s in pod.obj["status"]["containerStatuses"] if s["ready"]]
            )
            ready_style = (
                "[orange3]" if n_ready_containers < n_containers else "[green]"
            )
            start_time = datetime.strptime(
                pod.obj["metadata"]["creationTimestamp"], TIMESTAMP_FORMAT
            )
            restarts = str(pod.obj["status"]["containerStatuses"][0]["restartCount"])
            last_restart = datetime.strptime(
                list(pod.obj["status"]["containerStatuses"][0]["state"].values())[0][
                    "startedAt"
                ],
                TIMESTAMP_FORMAT,
            )
            labels = (
                [
                    ",".join(
                        [
                            f"{key}={value}"
                            for key, value in pod.obj["metadata"]["labels"].items()
                        ]
                    )
                ]
                if show_labels
                else []
            )
            column_labels = [
                pod.obj["metadata"]["labels"].get(label, "") for label in label_columns
            ]
            table.add_row(
                name,
                f"{ready_style}{n_ready_containers}/{n_containers}",
                pod.obj["status"]["phase"],
                f"{restarts} ({time_delta_to_string(datetime.now() - last_restart, 1, ' ago')})",
                time_delta_to_string(datetime.now() - start_time, 2),
                *labels,
                *column_labels,
            )
        console.print(table)
