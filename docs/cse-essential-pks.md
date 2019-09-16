# Enabling VMware Essential PKS in Container Service Extension

## Container Service Extension (CSE) Reference Links

- [Container Service Extension official docs](https://vmware.github.io/container-service-extension/INTRO.html)
- [Container Service Extension on pypi](https://pypi.org/project/container-service-extension/)
- [Container Service Extension Github](https://github.com/vmware/container-service-extension)

---

## Essential PKS Template Details

| ubuntu-16.04_esspks-1.15_weave-2.5.2 | Revision 1 (latest)                                                                                             |
| ------------------------------------ | --------------------------------------------------------------------------------------------------------------- |
| Ubuntu                               | 16.04 (https://cloud-images.ubuntu.com/releases/xenial/release-20180418/ubuntu-16.04-server-cloudimg-amd64.ova) |
| Docker                               | 18.09.7 (docker-ce=5:18.09.7\~3-0\~ubuntu-xenial)                                                                 |
| Kubernetes                           | [Essential PKS Kubernetes 1.15.3](https://hub.heptio.com/releases/1-15-release/#1-15-3)                         |
| Weave (cluster CNI)                  | [2.5.2](https://www.weave.works/docs/net/latest/overview/)                                                      |
| Default compute policy name          | essential-pks                                                                                                   |
| Default number of vCPUs              | 2                                                                                                               |
| Default memory                       | 2048 mb                                                                                                         |

---

## Creating Essential PKS Kubernetes Template using CSE

*A CSE config file should be created and should contain your vCloud Director details. More CSE config file details can be found [here](https://vmware.github.io/container-service-extension/CSE_ADMIN.html#configfile)*

1. In the CSE config file, change the value of the key `remote_template_cookbook_url` to  `https://raw.githubusercontent.com/vmware/container-service-extension-templates/essential-pks/template.yaml`
2. Use CSE's command-line interface to create Essential PKS K8s template on vCloud Director
   - Installing (or re-installing) CSE on vCloud Director will create any new templates if they are specified in the CSE config file
     ```$ cse install -c path/to/myconfig.yaml```
   - CSE's template installation command can be used to create new templates once CSE is already installed on vCloud Director
     ```$ cse template install -c myconfig.yaml ubuntu-16.04_esspks-1.15_weave-2.5.2 1``` (*1 is the template revision number*)
3. In the vCloud Director organization specified in the CSE config file, you should see the Essential PKS Kubernetes template (**ubuntu-16.04_esspks-1.15_weave-2.5.2_rev1**) in the catalog (also specified in the CSE config file). Users can now create Essential PKS Kubernetes clusters using CSE `vcd cse cluster create ...` command.

---

## Protecting Essential PKS Template

Essential PKS template has a default compute policy named **essential-pks**. Users will not be able to deploy templates to org VDCs that do not have the specified compute policy assigned. System administrators can assign compute policies to org VDCs via CSE's command-line interface. More information on how CSE uses compute policies can be found [here](TODO)

### Enabling/Disabling Deployment of Essential PKS Clusters

*Only system administrator can use `vcd cse ovdc compute-policy ...` commands*

```bash
# must be logged in as system administrator
$ vcd login IP system administrator

# assign 'essential-pks' compute policy to your org VDC
$ vcd cse ovdc compute-policy add ORG_NAME OVDC_NAME essential-pks

# confirm that the compute policy is assigned
$ vcd cse ovdc compute-policy list ORG_NAME OVDC_NAME

# remove 'essential-pks' compute policy from an org VDC (to disable deployments)
$ vcd cse ovdc compute-policy remove ORG_NAME OVDC_NAME essential-pks
```

### Changing Essential PKS Template's Compute Policy

System administrators can change or remove Essential PKS template's compute policy using CSE's template rule functionality. These changes require server startup to take effect.

Append this section to CSE config file:

```yaml
template_rules:
- name: Rule1 # name is only for error printing purposes
  target:
    name: ubuntu-16.04_esspks-1.15_weave-2.5.2
    revision: 1
  action:
    compute_policy: 'my-compute-policy' # if this value is '', compute_policy will be removed instead
```

*if compute_policy key is omitted, the template's default compute policy will be used*
