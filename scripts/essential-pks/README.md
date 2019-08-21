# Essential PKS - CSE POC (June 7, 2019)

*Not a full implementation of Essential PKS template support (such as our current native ubuntu and photon templates)*

[**Scripts for Essential PKS k8s template**](https://github.com/andrew-ni/container-service-extension/tree/essential-pks-poc/scripts/essential-pks)

---

## Using this POC

```bash
# download the repo branch that contains the POC
$ git clone -b essential-pks-poc https://github.com/andrew-ni/container-service-extension

# pip install cse using the downloaded directory filepath (don't forget that '/' at the end)
$ pip install container-service-extension/

$ cd container-service-extension/scripts/essential-pks
# `ls` should show 5 script files and a README

# create a sample CSE config file and fill it in with your vCD details
$ cse sample -o myconfig.yaml

$ cse install --config myconfig.yaml --template ubuntu-16.04 --update

# `--skip-check` is required since we only installed ubuntu template
$ cse run --config myconfig.yaml --skip-check

$ vcd login VCD_IP ORG_NAME USERNAME -iwp PASSWORD
# edit '~/.vcd-cli/profiles.yaml' to include this additional section to enable CSE client in vcd-cli
#
# extensions:
# - container_service_extension.client.cse

$ vcd cse cluster create --template ubuntu-16.04 --ssh-key ~/.ssh/id_rsa.pub --nodes 1 --network NETWORK_NAME my-essential-pks-cluster

# test that cluster is set up correctly
$ vcd cse cluster config my-essential-pks-cluster > ~/.kube/config
$ kubectl get nodes
```

*Follow instructions here to deploy a sample kubernetes application: <https://kubernetes.io/docs/tutorials/stateless-application/guestbook/#start-up-the-redis-master>*

*You can also ssh into the cluster VMs and inspect installed packages, hosted container images, and running containers*

---

## Notes

This POC uses:

- Kubernetes 1.14.2 components from Essential PKS
- weave 2.5.2 (<https://www.weave.works/docs/net/latest/install/installing-weave/)>
- **cust-ubuntu-16.04.sh** self-hosts Kubernetes-required container images on a local docker image registry.
  - This is done because Essential PKS has not exposed a public image repository (such as **k8s.gcr.io**).
  - To tell **kubeadm** to use this image repository instead of the default **k8s.gcr.io**, we add `--image-repository "localhost:5000"` to the `kubeadm init` command in **mstr-ubuntu-16.04.sh**.

---

## References

- <https://kubernetes.io/docs/reference/setup-tools/kubeadm/kubeadm-init/>
- <https://docs.docker.com/registry/deploying/>
- <https://www.weave.works/docs/net/latest/install/installing-weave/>
