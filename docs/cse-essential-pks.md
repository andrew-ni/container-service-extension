# Enabling VMware Essential PKS in Container Service Extension

Container Service Extension 2.5 enables orchestration of Kubernetes clusters with VMware Essential PKS in VMware vCloud Director powered clouds. It comes with the built-in capability to leverage VMware Essential PKS through the Essential PKS template. In order to turn on this capability, please see the section **Creating VMware Essential PKS Template using Container Service Extension**. The details of VMware Essential PKS template used in Container Service Extension are highlighted in the section **VMware Essential PKS Template Details**.

---

## Container Service Extension (CSE) Reference Links

- [Container Service Extension official docs](https://vmware.github.io/container-service-extension/INTRO.html)
- [Container Service Extension on pypi](https://pypi.org/project/container-service-extension/)
- [Container Service Extension Github](https://github.com/vmware/container-service-extension)

---

## VMware Essential PKS Template Details

| Attribute                   | Value                                                                                                            |
|-----------------------------|------------------------------------------------------------------------------------------------------------------|
| Template name               | ubuntu-16.04_esspks-1.15_weave-2.5.2                                                                             |
| Latest Revision             | 1                                                                                                                |
| Catalog item name           | ubuntu-16.04_esspks-1.15_weave-2.5.2_rev1                                                                        |
| Template details URL        | <https://raw.githubusercontent.com/vmware/container-service-extension-templates/essential-pks/template.yaml>     |
| Ubuntu version              | [16.04](https://cloud-images.ubuntu.com/releases/xenial/release-20180418/ubuntu-16.04-server-cloudimg-amd64.ova) |
| Docker version              | 18.09.7 (docker-ce=5:18.09.7\~3-0\~ubuntu-xenial)                                                                |
| Kubernetes version          | [VMware Essential PKS Kubernetes 1.15.3](https://hub.heptio.com/releases/1-15-release/#1-15-3)                   |
| Weave version               | [2.5.2](https://www.weave.works/docs/net/latest/overview/)                                                       |
| Default compute policy name | essential-pks                                                                                                    |
| Default number of vCPUs     | 2                                                                                                                |
| Default memory              | 2048 mb                                                                                                          |

---

## Creating VMware Essential PKS Template using Container Service Extension

*A CSE config file should be created and should contain your VMware vCloud Director details. More CSE config file details can be found [here](https://vmware.github.io/container-service-extension/CSE_ADMIN.html#configfile)*

1. In the CSE config file, change the value of the key `remote_template_cookbook_url` to  `https://raw.githubusercontent.com/vmware/container-service-extension-templates/essential-pks/template.yaml`. This change enables CSE to view the source of VMware Essential PKS Template.
2. Create VMware Essential PKS template in VMware vCloud Director using CSE's command-line interface by choosing one of these two ways:
   - Install or re-install CSE 2.5 on VMware vCloud Director to create new VMware Essential PKS template as specified in the CSE config file. The existing templates that were installed by CSE will not be affected.
     - ```$ cse install -c path/to/myconfig.yaml```
   - Use CSE's template install command to create new VMware Essential PKS template after CSE is already installed on VMware vCloud Director (check VMware Essential PKS Template Details section for parameter values).
     - ```$ cse template install -c path/to/myconfig.yaml TEMPLATE_NAME TEMPLATE_REVISION_NUMBER```
3. In the VMware vCloud Director organization specified in the CSE config file, you should see the VMware Essential PKS template in the catalog (also specified in the CSE config file).

Users can now create VMware Essential PKS Kubernetes clusters using CSE. For VMware vCloud Director 10, please follow the section **Deployment of Kubernetes clusters from VMware Essential PKS Template**

---

## Deployment of Kubernetes clusters from VMware Essential PKS Template

VMware Essential PKS template created by CSE has a default compute policy "essential-pks". This policy is used to restrict Kubernetes cluster deployments to organization VDCs that have the matching policy in VMware vCloud Director. In order to enable Kubernetes cluster deployments using this template, system administrator needs to add the policy to the desired organization VDCs. More information on how CSE uses compute policies can be found [here](TODO)

Use CSE's command line interface to run below commands to add the policy to an organization VDC.

```bash
# must be logged in as system administrator
$ vcd login VCD_IP system administrator

# assign 'essential-pks' compute policy to your org VDC
$ vcd cse ovdc compute-policy add ORG_NAME OVDC_NAME essential-pks

# confirm that the compute policy is assigned to your org VDC
$ vcd cse ovdc compute-policy list ORG_NAME OVDC_NAME
```

*Only system administrator can use `vcd cse ovdc compute-policy ...` commands*

*Restricting deployments from VMware Essential PKS template is only available on VMware vCloud Director 10. There is no way to restrict deployments from VMware Essential PKS template on older VMware vCloud Director versions.*

Please refer to [here](TODO) for further information on enabling VMware Essential PKS.
