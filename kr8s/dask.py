from dask_kubernetes.aiopykube.objects import NamespacedAPIObject


class DaskCluster(NamespacedAPIObject):
    version = "kubernetes.dask.org/v1"
    endpoint = "daskclusters"
    kind = "DaskCluster"


class DaskWorkerGroup(NamespacedAPIObject):
    version = "kubernetes.dask.org/v1"
    endpoint = "daskworkergroups"
    kind = "DaskWorkerGroup"


class DaskAutoscaler(NamespacedAPIObject):
    version = "kubernetes.dask.org/v1"
    endpoint = "daskautoscalers"
    kind = "DaskAutoscaler"


class DaskJob(NamespacedAPIObject):
    version = "kubernetes.dask.org/v1"
    endpoint = "daskjobs"
    kind = "DaskJob"
