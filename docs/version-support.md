# Version Support

We endeavor to support all Kubernetes versions that are [actively supported by the Kubernetes community](https://kubernetes.io/releases/) and popular cloud hosted Kubernetes platforms.

For each version of Kubernetes we check the following end of life dates:
- [Open Source Kubernetes Maintenance Support](https://endoflife.date/kubernetes)
- [Google Kubernetes Engine Maintenance Support](https://endoflife.date/google-kubernetes-engine)
- [Amazon EKS End of Support](https://endoflife.date/amazon-eks)
- [Azure Kubernetes Service End of Support](https://endoflife.date/azure-kubernetes-service)

Once a version has reached end of life from all providers we remove it from our CI/testing matrix.

Typically new versions are released 3-4 times a year and each version receives 12-15 months of support.

## Extended Support

Some cloud providers give extended or long term support. For example [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine/versioning) provides 14 months of standard support, and an additional 10 months of extended support.

In `kr8s` we understand that many folks make use of this extended support for production clusters. We aim to support these versions on a best efforts basis. We do not guarantee that extended support versions will be run in CI and may not actively fix bugs for those versions, but we are happy to accept pull requests targeting Kubernetes versions in extended support.
