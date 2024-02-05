# Releasing

To publish a new release of `kr8s` first make a new git tag. Releases follow [EffVer](https://jacobtomlinson.dev/effver) and have a `v` prefix. Then push the tag to the upstream `kr8s-org/kr8s` repo.

```console
$ git tag v0.0.0

$ git push upstream main --tags

```

This will trigger a [release GitHub Action](https://github.com/kr8s-org/kr8s/blob/main/.github/workflows/release.yaml) which will build and publish to PyPI.
