import collections
import inspect
import typer
from pathlib import Path
from rich.console import Console
import subprocess

app = typer.Typer(name="remote")
console = Console()

@app.callback()
def remote_main():
    console.print("""
    📶  Connect multiple AutoGOAL instances and share algorithms.
    """)


@app.command("connect")
def remote_connect(
    ip: str = typer.Argument(None, help="Interface ip to be used by the HTTP API"),
    port: int = typer.Argument(None, help="Port to be bind by the server"),
    connection_alias: int = typer.Argument(
        None,
        help="Connection alias for future references to the remote AutoGOAL instance",
    ),
    verbose: bool = False,
):
    try:
        import autogoal_remote as rm_server
    except:
        raise Exception("autogoal-remote not installed")

    try:
        from autogoal_contrib import find_remote_classes
    except:
        raise Exception("autogoal-contrib not installed")

    from autogoal_contrib import (
        find_remote_classes,
    )

    """
    📡  Connect to an existing AutoGOAL instance.
    """

    # try connection and request algorithms
    sources = []
    if ip is None or port is None:
        if connection_alias is not None:
            sources.append(connection_alias)
    else:
        if connection_alias is not None:
            sources.append((ip, port, connection_alias))
        else:
            sources.append((ip, port))

    classes = find_remote_classes(sources)

    typer.echo(f"⚙️  Successfully connected to remote AutoGOAL!", color="green")

    if connection_alias:
        typer.echo(
            f"⚙️  Stored connection to {ip}:{port} with alias '{connection_alias}' for future usage.",
            color="blue",
        )

    classes_by_contrib = collections.defaultdict(list)
    max_cls_name_length = 0

    for cls in classes:
        classes_by_contrib[cls.contrib].append(cls)

    typer.echo(
        f"⚙️  Found a total of {len(classes)} matching remote algorithms.", color="blue"
    )

    for contrib, clss in classes_by_contrib.items():
        typer.echo(f"🛠️  {connection_alias} -> {contrib}: {len(clss)} algorithms.")

        if verbose:
            for cls in clss:
                sig = inspect.signature(cls.run)
                typer.echo(
                    f" 🔹 {cls.__name__.ljust(max_cls_name_length)} : {sig.parameters['input'].annotation} -> {sig.return_annotation}"
                )


@app.command("share-contribs")
def share_contribs(
    ip: str = typer.Argument(
        "0.0.0.0", help="Interface ip of listening AutoGOAL service"
    ),
    port: int = typer.Argument(8000, help="Port of listening AutoGOAL service"),
):
    """
    Expose algorithms from installed contribs to other AutoGOAL instances over the network.
    """

    try:
        import autogoal_remote as rm_server
    except:
        raise Exception("autogoal-remote installation not detected")

    rm_server.distributed.run(ip, port)


@app.command("serve")
def automl_server(
    path: str = typer.Argument(None, help="Autogoal serialized model"),
    ip: str = typer.Argument("0.0.0.0", help="Interface ip to be used by the HTTP API"),
    port: int = typer.Argument(8000, help="Port to be bind by the server"),
):
    """
    Load and serve a previously trained AutoML instance as a service.
    """
    from autogoal.ml import AutoML
    from autogoal_remote.production import run
    import os

    default_path = Path(os.getcwd()) / "autogoal-export"
    console.print(f"Loading model from folder: {path or default_path}")
    model = AutoML.folder_load(Path(path or default_path))
    run(model, ip, port)


global typer_app
typer_app = app

if __name__ == "__main__":
    from autogoal.ml import AutoML
    from autogoal_remote.production import run
    import os

    default_path = Path(os.getcwd()) / "autogoal-export"
    console.print(f"Loading model from folder: {default_path}")
    model = AutoML.folder_load(Path(default_path))
    run(model, "0.0.0.0", 8000)
