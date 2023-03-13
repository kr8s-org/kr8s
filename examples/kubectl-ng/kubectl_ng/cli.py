import typer
from . import get

app = typer.Typer()
app.add_typer(get.app, name="get")

def go():
    app()

if __name__ == "__main__":
    go()
