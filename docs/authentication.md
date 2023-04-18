# Authentication

Configuring authentication in `kr8s` is optional as it will check the paths that `kubectl` uses.

```python
import kr8s

client = kr8s.api()
```

Lookup order:

- `~/.kube/config`
- `/var/run/secrets/kubernetes.io/serviceaccount`

When reading from a kube config file the following authentication methods are supported:

- Client certificate
- Token
- Exec

```{warning}
Legacy `auth-provider` methods are not currently supported along with OIDC.
```

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

```python
import kr8s

client = kr8s.api(url="127.0.0.1:8001")
```

### Kube Config

By default the first place `kr8s` will look for configuration is in `~/.kube/config`. However you can point it anywhere else of the system if your configuration is stored at another location.

```python
import kr8s

client = kr8s.api(kubeconfig="/path/to/kube/config")
```

### Service Account

When running inside a Pod with a service account, credentials will be mounted into `/var/run/secrets/kubernetes.io/serviceaccount` so `kr8s` will also check there. However you can specify an alternate path if you know that service account style credentials are stored elsewhere.

```python
import kr8s

client = kr8s.api(serviceaccount="/path/to/kube/config")
```
