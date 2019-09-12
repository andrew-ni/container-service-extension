# CSE and Essential PKS

## CSE Reference Links

- [CSE official docs](https://vmware.github.io/container-service-extension/INTRO.html)
- [CSE on pypi](https://pypi.org/project/container-service-extension/)
- [CSE Github](https://github.com/vmware/container-service-extension)

---

## Essential-PKS Template Details

| ubuntu-16.04_esspks-1.15_weave-2.5.2 | Revision 1 (latest)                                                                                             |
| ------------------------------------ | --------------------------------------------------------------------------------------------------------------- |
| Ubuntu                               | 16.04 (https://cloud-images.ubuntu.com/releases/xenial/release-20180418/ubuntu-16.04-server-cloudimg-amd64.ova) |
| Docker                               | 18.09.7 (docker-ce=5:18.09.7~3-0~ubuntu-xenial)                                                                 |
| Kubernetes                           | [Essential PKS Kubernetes 1.15.3](https://hub.heptio.com/releases/1-15-release/#1-15-3)                         |
| Weave (cluster CNI)                  | [2.5.2](https://www.weave.works/docs/net/latest/overview/)                                                      |
| Default compute policy name          | essential-pks                                                                                                   |
| Default number of vCPUs              | 2                                                                                                               |
| Default memory                       | 2048 mb                                                                                                         |

---

## Creating Essential-PKS Kubernetes vApp Template using CSE

1. In CSE config file, change the value of the key `remote_template_cookbook_url` to  `https://raw.githubusercontent.com/vmware/container-service-extension-templates/essential-pks/template.yaml`
2. Create Essential-PKS K8s templates using CSE following one of the below methods
   - ```$ cse install -c myconfig.yaml```
   - ```$ cse template install -c myconfig.yaml ubuntu-16.04_esspks-1.15_weave-2.5.2 1``` (*1 is the template revision number*)
3. In the vCD catalog specified in the CSE config file, you should see the essential-pks Kubernetes template as a catalog item named **ubuntu-16.04_esspks-1.15_weave-2.5.2_rev1**. Users can now use CSE's `vcd cse cluster create` command to create clusters.

---

## Protecting Essential-PKS Template

CSE templates are protected via **vCD compute policy**. If a CSE template has a compute policy and the org VDC that a user is trying to deploy to does not have that specific compute policy assigned to it, then the deployment will fail. Essential-PKS template has a default compute policy named **essential-pks**.

### Enabling/Disabling Deployment of Essential-PKS Clusters

*only system administrator can use `vcd cse ovdc compute-policy ...` commands*

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

### Changing Compute Policy of Essential-PKS Template

System administrators can change or remove Essential-PKS template's compute policy using CSE's template rule functionality. These changes require server startup to take effect.

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
