# Labelling Operator

Build an operator that periodically reconciles all Deployments and adds a label to any with a certain annotation.

```{warning}
While you can build operators with `kr8s` we would recommend folks look at using [kopf](https://kopf.readthedocs.io/en/stable/) for building anything more complex than the below example.
```

## Controller

First we need to create a Python script called `controller.py` containing the controller code that uses `kr8s`.

`````{tab-set}

````{tab-item} Sync
```python
# controller.py
import time
import kr8s

def run():
    while True:
        for deploy in kr8s.get("deployments", namespace=kr8s.ALL):
            if 'pykube-test-operator' in deploy.annotations:
                deploy.label(foo="bar")
        time.sleep(15)

if __name__ == "__main__":
    run()
```
````

````{tab-item} Async
```python
# controller.py
import asyncio
import kr8s

async def run():
    while True:
        for deploy in await kr8s.asyncio.get("deployments", namespace=kr8s.ALL):
            if 'pykube-test-operator' in deploy.annotations:
                await deploy.label(foo="bar")
        await asyncio.sleep(15)

if __name__ == "__main__":
    asyncio.run(run())
```
````

`````

## Packaging

Now we can package our controller code in a container image.

```dockerfile
# Dockerfile
FROM python:3.11

WORKDIR /usr/local/src

RUN pip install kr8s

COPY controller.py /usr/local/src/

CMD ["python3", "/usr/local/src/controller.py"]
```

```console
$ docker build -t foo/labelling-operator:latest .
$ docker push foo/labelling-operator:latest
```

## Deploying

Then to deploy our operator we need to create a ServiceAccount with a ClusterRole for our controller to use to communicate with the Kubernetes API.

```yaml
# rbac.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: labelling-operator
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: labelling-operator
rules:
- apiGroups:
  - apps
  resources:
  - deployments
  verbs:
  - get
  - watch
  - list
  - update
  - patch
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: labelling-operator
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: labelling-operator
subjects:
- kind: ServiceAccount
  name: labelling-operator
  namespace: default
```

```console
$ kubectl apply -f rbac.yaml
```

Then create a deployment to run our controller container.

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: labelling-operator
spec:
  replicas: 1
  selector:
    matchLabels:
      app: labelling-operator
  template:
    metadata:
      labels:
        app: labelling-operator
    spec:
      serviceAccountName: labelling-operator
      containers:
      - name: operator
        image: foo/labelling-operator:latest
```

```console
$ kubectl apply -f deployment.yaml
```
