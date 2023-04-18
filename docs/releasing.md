# Releasing

To publish a new release of `kr8s` first make a new git tag. Release follow SemVer and have a `v` prefix.

```console
$ git tag v0.0.0

```

Then publish to PyPI with `poetry`.

```console
$ poetry publish --build

```
