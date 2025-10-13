# Version Support

We endeavor to support all Kubernetes versions that are [actively supported by the Kubernetes community](https://kubernetes.io/releases/) and popular cloud hosted Kubernetes platforms.

For each version of Kubernetes we check the following end of life dates:
- [Open Source Kubernetes Maintenance Support](https://endoflife.date/kubernetes)
- [Google Kubernetes Engine Maintenance Support](https://endoflife.date/google-kubernetes-engine)
- [Amazon EKS End of Support](https://endoflife.date/amazon-eks)
- [Azure Kubernetes Service End of Support](https://endoflife.date/azure-kubernetes-service)

<!-- BEGIN: VERSION_TABLE -->
| Kubernetes Version | Support Until | Source of Support |
|--------------------|---------------|-------------------|
| 1.33 | 2027-07-29 |  <br> - Azure AKS Extended Support <br> - Amazon EKS |
| 1.32 | 2027-03-31 | - Azure AKS Extended Support |
| 1.31 | 2026-11-30 | - Azure AKS Extended Support |
| 1.30 | 2026-07-31 | - Azure AKS Extended Support |
| 1.29 | 2026-04-30 | - Azure AKS Extended Support |
| 1.28 | 2026-02-28 | - Azure AKS Extended Support |
<!-- END: VERSION_TABLE -->

Once a version has reached end of life from all providers we remove it from our CI/testing matrix.

Typically new versions are released 3-4 times a year and each version receives 12-15 months of support.

## Extended Support

Some cloud providers give extended or long term support. For example [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine/versioning) provides 14 months of standard support, and an additional 10 months of extended support.

In `kr8s` we understand that many folks make use of this extended support for production clusters. We aim to support these versions on a best efforts basis. We do not guarantee that extended support versions will be run in CI and may not actively fix bugs for those versions, but we are happy to accept pull requests targeting Kubernetes versions in extended support.
