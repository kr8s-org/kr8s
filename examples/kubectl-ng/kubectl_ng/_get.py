# SPDX-FileCopyrightText: Copyright (c) 2023-2025, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License

from datetime import datetime

import anyio
import rich.table
import typer
from rich import box
from rich.console import Console
from rich.live import Live
from rich.text import Text

import kr8s
from kr8s._async_utils import anext
from kr8s.asyncio.objects import Table

TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
CHANGE_INDICATOR_DURATION = 15  # seconds to show change indicators
EXCLUDED_CHANGE_COLUMNS = ["Age"]  # columns to exclude from change indicators

# Unicode symbols for changes with their styles
UP_ARROW = Text("↑", style="green")
DOWN_ARROW = Text("↓", style="red")
CHANGE_DELTA = Text("Δ", style="cyan")


def is_numeric(value):
    """Check if a string value can be converted to a number."""
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False


def get_change_indicator(old_value, new_value):
    """Get the appropriate change indicator based on value comparison."""
    if not is_numeric(old_value) or not is_numeric(new_value):
        return CHANGE_DELTA if old_value != new_value else Text("")

    old_num = float(old_value)
    new_num = float(new_value)

    if new_num > old_num:
        return UP_ARROW
    elif new_num < old_num:
        return DOWN_ARROW
    return Text("")


console = Console()


async def draw_table(
    kind, response, resource_names, previous_state=None, last_update_time=None
):
    table = rich.table.Table(box=box.SIMPLE)
    table.add_column("Namespace", style="magenta", no_wrap=True)

    for column in response.column_definitions:
        if column["priority"] == 0:
            kwargs = {}
            if column["name"] == "Name":
                kwargs = {"style": "cyan", "no_wrap": True}
            table.add_column(column["name"], **kwargs)

    current_time = datetime.now()
    show_indicators = (
        last_update_time
        and (current_time - last_update_time).total_seconds()
        < CHANGE_INDICATOR_DURATION
    )

    for row in response.rows:
        if not resource_names or row["object"]["metadata"]["name"] == resource_names[0]:
            cells = []
            for cell, column in zip(row["cells"], response.column_definitions):
                if column["priority"] == 0:
                    cell_str = str(cell)
                    if (
                        show_indicators
                        and previous_state
                        and column["name"] not in EXCLUDED_CHANGE_COLUMNS
                    ):
                        # Find matching previous row
                        prev_row = next(
                            (
                                r
                                for r in previous_state.rows
                                if r["object"]["metadata"]["name"]
                                == row["object"]["metadata"]["name"]
                                and r["object"]["metadata"]["namespace"]
                                == row["object"]["metadata"]["namespace"]
                            ),
                            None,
                        )
                        if prev_row:
                            prev_cell = next(
                                (
                                    c
                                    for c, col in zip(
                                        prev_row["cells"],
                                        previous_state.column_definitions,
                                    )
                                    if col["priority"] == 0
                                    and col["name"] == column["name"]
                                ),
                                None,
                            )
                            if prev_cell is not None:
                                indicator = get_change_indicator(
                                    str(prev_cell), cell_str
                                )
                                if indicator:
                                    cell_str = indicator + Text(" ") + Text(cell_str)
                    cells.append(cell_str)
            table.add_row(row["object"]["metadata"]["namespace"], *cells)

    if not table.rows:
        if resource_names:
            console.print(f"No resources found with name {resource_names[0]}.")
        else:
            console.print(f"No {kind} resources found in current namespace.")
        return None
    return table


async def get_resources(resources, label_selector, field_selector):
    data = {}
    for kind in resources:
        data[kind] = await anext(
            kr8s.asyncio.get(
                kind,
                label_selector=label_selector,
                field_selector=field_selector,
                as_object=Table,
            )
        )
    return data


async def get(
    resources: list[str] = typer.Argument(..., help="TYPE[.VERSION][.GROUP]"),
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
    label_selector: str = typer.Option(
        "",
        "-l",
        "--selector",
        help="Selector (label query) to filter on, supports '=', '==', and '!='. "
        "(e.g. -l key1=value1,key2=value2). "
        "Matching objects must satisfy all of the specified label constraints.",
    ),
    field_selector: str = typer.Option(
        "",
        "--field-selector",
        help="Selector (field query) to filter on, supports '=', '==', and '!='. "
        "(e.g. --field-selector key1=value1,key2=value2). "
        "The server only supports a limited number of field queries per type. ",
    ),
    show_kind: bool = typer.Option(
        False,
        "--show-kind",
        help="If present, list the resource type for the requested object(s).",
    ),
    show_labels: bool = typer.Option(
        False,
        "--show-labels",
        help="When printing, show all labels as the last column "
        "(default hide labels column).",
    ),
    label_columns: list[str] = typer.Option(
        [],
        "-L",
        "--label-columns",
        help="Accepts a comma separated list of labels that are going to be presented as columns. "
        "Names are case-sensitive. "
        "You can also use multiple flag options like -L label1 -L label2...",
    ),
    watch: bool = typer.Option(
        False,
        "-w",
        "--watch",
        help="After listing/getting the requested object, watch for changes.",
    ),
):
    """Display one or many resources.

    Prints a table of the most important information about the specified resources. You can filter the list using a
    label selector and the --selector flag. If the desired resource type is namespaced you will only see results
    in your current namespace unless you pass --all-namespaces.

    By specifying the output as 'template' and providing a Jinja2 template as the value of the --template flag, you
    can filter the attributes of the fetched resources.

    Use "kubectl-ng api-resources" for a complete list of supported resources.
    """
    resource_names = []
    # Support kubectl-ng get pod,svc
    if len(resources) == 1:
        resources = resources[0].split(",")
        if len(resources) > 1 and watch:
            raise typer.BadParameter("you may only specify a single resource type")
    # Support kubectl-ng get pod [name]
    elif len(resources) == 2:
        resources, resource_names = ([r] for r in resources)
    else:
        raise typer.BadParameter(
            f"Format '{' '.join(resources)}' not currently supported."
        )
    kubernetes = await kr8s.asyncio.api()
    if namespace:
        kubernetes.namespace = namespace
    if all_namespaces:
        kubernetes.namespace = kr8s.ALL

    data = await get_resources(resources, label_selector, field_selector)

    if not watch:
        for kind, response in data.items():
            table = await draw_table(kind, response, resource_names)
            if table:
                console.print(table)
    else:
        kind = list(data)[0]
        response = data[kind]
        table = await draw_table(kind, response, resource_names)
        previous_state = None
        last_update_time = None

        with Live(table, console=console, auto_refresh=False) as live:
            while True:
                await anyio.sleep(5)
                previous_state = response
                last_update_time = datetime.now()
                data = await get_resources(resources, label_selector, field_selector)
                for kind, response in data.items():
                    table = await draw_table(
                        kind, response, resource_names, previous_state, last_update_time
                    )
                live.update(table)
                live.refresh()
