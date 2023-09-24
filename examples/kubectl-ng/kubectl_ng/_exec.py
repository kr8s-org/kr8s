from typing import List

import typer
from rich.console import Console

import kr8s

console = Console()


async def kexec(
    resource: str = typer.Argument(..., help="POD | TYPE/NAME"),
    namespace: str = typer.Option(
        None,
        "-n",
        "--namespace",
    ),
    container: str = typer.Option(
        None,
        "-c",
        "--container",
        help="Container name. "
        "If omitted, use the kubectl.kubernetes.io/default-container annotation "
        "for selecting the container to be attached or the first container in the "
        "pod will be chosen",
    ),
    command: List[str] = typer.Argument(..., help="COMMAND [args...]"),
):
    """Execute a command in a container."""
    pod = await kr8s.asyncio.objects.Pod(resource, namespace=namespace)
    console.print(pod.name)
    await pod.exec(command, container=container)
