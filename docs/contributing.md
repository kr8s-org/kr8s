# Contributing

Contributions are very welcome. Check out our [open issues on GitHub](https://github.com/kr8s-org/kr8s/issues).

## Development environment

We recommend you develop `kr8s` inside a virtual environment. We use [hatch](https://hatch.pypa.io/) for builds, virtual environments and task running, but you can use whatever you prefer.

```bash
pip install hatch
hatch shell  # Creates the hatch venv and activates it
```

But there are many different tools out there so feel free to use whichever you prefer and install `kr8s` in development mode.

```bash
# Create/activate your Python environment
pip install -e .
```

## Testing

Tests in `kr8s` are run with `pytest`. To handle testing again Kubernetes we also use [kind](https://kind.sigs.k8s.io/) via the [`pytest-kind`](https://pypi.org/project/pytest-kind/) plugin. Kind launches a Kubernetes cluster inside a single Docker container which is great for local development. All setup is handles via fixtures so as long as you have `docker` you can run the tests.

```bash
hatch run test:run
```

Or you can install the test dependencies and invoke `pytest` yourself.

```bash
pip install -e .[test]
pytest kr8s
```

## Documentation

Documentation is built with [Sphinx](https://www.sphinx-doc.org/en/master/). You can build the docs locally.

```bash
hatch run docs:serve
```

Or you can install the docs dependencies and invoke `sphinx-build` or `sphinx-autobuild` yourself.

```bash
pip install -e .[docs]
sphinx-autobuild docs docs/_build --ignore 'docs/autoapi/**/*' --host 0.0.0.0
```

## Linting

We lint `kr8s` with `black` and `ruff`. We recommend you install [`pre-commit`](https://pre-commit.com/) to do this on each commit.

```console
$ pip install pre-commit
$ pre-commit install
$ # You can manually run pre-commit on all files too
$ pre-commit run --all
```
