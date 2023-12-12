# Authentication

Configuring authentication in `kr8s` is optional as it will check the paths that `kubectl` uses.

`````{tab-set}

````{tab-item} Sync
:sync: sync
```python
import kr8s

client = kr8s.api()
```
````

````{tab-item} Async
:sync: async
```python
import kr8s.asyncio

client = await kr8s.asyncio.api()
```
````

`````

Lookup order:

- `~/.kube/config` (or the path set by the `KUBECONFIG` environment variable)
- `/var/run/secrets/kubernetes.io/serviceaccount`

When reading from a kube config file the following authentication methods are supported:

- Client certificate
- Token
- Exec
- OIDC

```{warning}
Support for the legacy `auth-provider` methods is not planned.
```

``````{tip}
To find out which user `kr8s` is currently authenticated with you can call `client.whoami()`.


`````{tab-set}

````{tab-item} Sync
:sync: sync
```python
print(client.whoami())
# 'kubernetes-admin'
```
````

````{tab-item} Async
:sync: async
```python
print(await client.whoami())
# 'kubernetes-admin'
```
````

`````

``````

## Manual configuration

You can also manually specify authentication information when you create your kr8s client object.

```{note}
When using the [Object API](object) you may not even need to create an API client, however when configuring credentials manually it can still be helpful to create an instance of the client via [](#kr8s.api) as this API client will be cached and reused by objects in the future.

See [Client Caching](client) for more information.
```

### URL

Connecting directly to a URL assumes no authentication information is necessary. This is most useful when using with `kubectl proxy` which proxies the Kubernetes API on `localhost` without requiring authentication.

```console
$ kubectl proxy
Starting to serve on 127.0.0.1:8001
```

`````{tab-set}

````{tab-item} Sync
:sync: sync
```python
import kr8s

client = kr8s.api(url="127.0.0.1:8001")
```
````

````{tab-item} Async
:sync: async
```python
import kr8s.asyncio

client = await kr8s.asyncio.api(url="127.0.0.1:8001")
```
````

`````

### Kube Config

By default the first place `kr8s` will look for configuration is in `~/.kube/config`. However you can point it anywhere else of the system if your configuration is stored at another location.

`````{tab-set}

````{tab-item} Sync
:sync: sync
```python
import kr8s

client = kr8s.api(kubeconfig="/path/to/kube/config")
```
````

````{tab-item} Async
:sync: async
```python
import kr8s.asyncio

client = await kr8s.asyncio.api(kubeconfig="/path/to/kube/config")
```
````

`````

#### Context

If you have multiple contexts in your config and you do not want to use the default or currently selected one you can set this explicitly.

`````{tab-set}

````{tab-item} Sync
:sync: sync
```python
import kr8s

client = kr8s.api(context="foo-context")
```
````

````{tab-item} Async
:sync: async
```python
import kr8s.asyncio

client = await kr8s.asyncio.api(context="foo-context")
```
````

`````

### Service Account

When running inside a Pod with a service account, credentials will be mounted into `/var/run/secrets/kubernetes.io/serviceaccount` so `kr8s` will also check there. However you can specify an alternate path if you know that service account style credentials are stored elsewhere.

`````{tab-set}

````{tab-item} Sync
:sync: sync
```python
import kr8s

client = kr8s.api(serviceaccount="/path/to/kube/config")
```
````

````{tab-item} Async
:sync: async
```python
import kr8s.asyncio

client = await kr8s.asyncio.api(serviceaccount="/path/to/kube/config")
```
````

`````
