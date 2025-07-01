# kubectl-ng

A reimplementation of `kubectl` using `kr8s`, `rich` and `typer`.

Just for fun, mostly to kick the tyres on `kr8s` and ensure it can do everything `kubectl` can do.

## Install

### Via `pip`/`pipx`

```
pipx install kubectl-ng
```

### Via `uv`

```
uv tool install kubectl-ng
```

## Usage

```
$ kubectl ng get pods
                                                                 
  Namespace   Name           Ready   Status    Restarts   Age    
 ─────────────────────────────────────────────────────────────── 
  default     examplevp7md   1/1     Running   0          4d21h  
```
