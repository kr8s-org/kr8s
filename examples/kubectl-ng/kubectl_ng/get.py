import typer

app = typer.Typer()


@app.command()
def pods():
    typer.echo("Pods")
