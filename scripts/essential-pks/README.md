# Essential PKS - CSE POC (June 7, 2019)

*Not a full implementation of Essential PKS template support (such as our current native ubuntu and photon templates)*

[**Scripts for Essential PKS k8s template**](https://github.com/andrew-ni/container-service-extension/tree/essential-pks-poc/scripts/essential-pks)

---

## Using this POC

1. Navigate to `container_service_extension/scripts/essential-pks/` (`ls` should show 5 script files and this README)
2. `cse install --config CONFIG.yaml --template ubuntu-16.04 --update`
3. `vcd cse cluster create --template ubuntu-16.04 --ssh-key ~/.ssh/id-rsa.pub --nodes 1 --network NETWORK_NAME essential-pks-cluster`
4. `vcd cse cluster config essential-pks-cluster > ~/.kube/config`
5. Follow instructions here to deploy a sample kubernetes application: https://kubernetes.io/docs/tutorials/stateless-application/guestbook/#start-up-the-redis-master

*You can also ssh into the cluster VMs and inspect installed packages, hosted container images, and running containers*

---

## Notes

This POC uses:

- Kubernetes 1.14.2 components from Essential PKS (latest)
- weave 2.5.2 (https://www.weave.works/docs/net/latest/install/installing-weave/)
- **cust-ubuntu-16.04.sh** self-hosts Kubernetes-required container images on a local docker image registry.
  - This is done because Essential PKS has not exposed a public image repository (such as **k8s.gcr.io**).
  - To tell **kubeadm** to use this image repository instead of the default **k8s.gcr.io**, we add `--image-repository "localhost:5000"` to the `kubeadm init` command in **mstr-ubuntu-16.04.sh**.
