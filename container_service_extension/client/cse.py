# container-service-extension
# Copyright (c) 2017 VMware, Inc. All Rights Reserved.
# SPDX-License-Identifier: BSD-2-Clause
import os

import click
from vcd_cli.utils import stderr
from vcd_cli.utils import stdout
from vcd_cli.vcd import vcd
import yaml

from container_service_extension.client import pks
from container_service_extension.client.cluster import Cluster
import container_service_extension.client.command_filter as cmd_filter
import container_service_extension.client.constants as cli_constants
from container_service_extension.client.de_cluster_native import DEClusterNative  # noqa: E501
from container_service_extension.client.ovdc import Ovdc
import container_service_extension.client.sample_generator as client_sample_generator  # noqa: E501
from container_service_extension.client.system import System
from container_service_extension.client.template import Template
import container_service_extension.client.utils as client_utils
from container_service_extension.exceptions import CseResponseError
from container_service_extension.exceptions import CseServerNotRunningError
from container_service_extension.logger import CLIENT_LOGGER
from container_service_extension.minor_error_codes import MinorErrorCode
from container_service_extension.server_constants import K8S_PROVIDER_KEY
from container_service_extension.server_constants import K8sProvider
from container_service_extension.server_constants import LocalTemplateKey
import container_service_extension.shared_constants as shared_constants
import container_service_extension.utils as utils


@vcd.group(short_help='Manage Kubernetes clusters',
           cls=cmd_filter.GroupCommandFilter)
@click.pass_context
def cse(ctx):
    """Manage Kubernetes clusters (Native, vSphere with Tanzu and Ent-PKS).

    Once logged-in, few cmd groups may remain hidden based on factors like
    a) the API version with which CSE server is running
    b) whether CSE server is running or not.

    If CSE server is not running, "Cluster" command group can be used to
    manage "vSphere with Tanzu" clusters only.

    Note that re-login is required for CLI to effectively process any changes
     in the above mentioned external factors.
    """


@cse.command(short_help='Display CSE version')
@click.pass_context
def version(ctx):
    """Display version of CSE plug-in."""
    CLIENT_LOGGER.debug(f'Executing command: {ctx.command_path}')
    cse_info = utils.get_cse_info()
    ver_str = '%s, %s, version %s' % (cse_info['product'],
                                      cse_info['description'],
                                      cse_info['version'])
    stdout(cse_info, ctx, ver_str)
    CLIENT_LOGGER.debug(ver_str)


@cse.group(short_help='Manage native kubernetes runtime templates')
@click.pass_context
def template(ctx):
    """Manage native kubernetes runtime templates.

\b
Examples
    vcd cse template list
        Display templates that can be used to deploy native clusters.
    """
    pass


@template.command('list',
                  short_help='List native kubernetes runtime templates')
@click.pass_context
def list_templates(ctx):
    """Display templates that can be used to deploy native clusters."""
    CLIENT_LOGGER.debug(f'Executing command: {ctx.command_path}')
    try:
        client_utils.cse_restore_session(ctx)
        client = ctx.obj['client']
        template = Template(client)
        result = template.get_templates()
        CLIENT_LOGGER.debug(result)
        value_field_to_display_field = {
            'name': 'Name',
            'revision': 'Revision',
            'is_default': 'Default',
            'catalog': 'Catalog',
            'catalog_item': 'Catalog Item',
            'description': 'Description'
        }
        filtered_result = client_utils.filter_columns(result, value_field_to_display_field)  # noqa: E501
        stdout(filtered_result, ctx, sort_headers=False)
    except Exception as e:
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))


@cse.group('cluster', cls=cmd_filter.GroupCommandFilter,
           short_help='Manage Kubernetes clusters (native and vSphere with '
                      'Tanzu)')
@click.pass_context
def cluster_group(ctx):
    """Manage Kubernetes clusters (Native, vSphere with Tanzu and Ent-PKS).

\b
Cluster names should follow the syntax for valid hostnames and can have
up to 25 characters .`system`, `template` and `swagger*` are reserved
words and cannot be used to name a cluster.
    """
    pass


@cluster_group.command('list',
                       short_help='Display clusters in vCD that are visible '
                                  'to the logged in user')
@click.pass_context
@click.option(
    '-v',
    '--vdc',
    'vdc',
    required=False,
    default=None,
    metavar='VDC_NAME',
    help='Filter list to show clusters from a specific org VDC')
@click.option(
    '-o',
    '--org',
    'org_name',
    default=None,
    required=False,
    metavar='ORG_NAME',
    help="Filter list to show clusters from a specific org")
def list_clusters(ctx, vdc, org_name):
    """Display clusters in vCD that are visible to the logged in user.

\b
Examples
    vcd cse cluster list
        Display clusters in vCD that are visible to the logged in user.
\b
    vcd cse cluster list -vdc ovdc1
        Display clusters in vdc 'ovdc1'.
    """
    CLIENT_LOGGER.debug(f'Executing command: {ctx.command_path}')
    try:
        client_utils.cse_restore_session(ctx)
        client = ctx.obj['client']
        cluster = Cluster(client)
        if not client.is_sysadmin() and org_name is None:
            org_name = ctx.obj['profiles'].get('org_in_use')
        clusters = cluster.list_clusters(vdc=vdc, org=org_name)
        stdout(clusters, ctx, show_id=True, sort_headers=False)
    except Exception as e:
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))


@cluster_group.command('delete',
                       short_help='Delete a cluster')
@click.pass_context
@click.argument('name', required=False, default=None)
@click.confirmation_option(prompt='Are you sure you want to delete the '
                                  'cluster?')
@click.option(
    '-v',
    '--vdc',
    'vdc',
    required=False,
    default=None,
    metavar='VDC_NAME',
    help='Restrict cluster search to specified org VDC')
@click.option(
    '-o',
    '--org',
    'org',
    default=None,
    required=False,
    metavar='ORG_NAME',
    help='Restrict cluster search to specified org')
@click.option(
    '-k',
    '--k8-runtime',
    'k8_runtime',
    default=None,
    required=False,
    metavar='K8-RUNTIME',
    help='Restrict cluster search to cluster kind; Supported only for'
         ' vcd api version >= 35')
@click.option(
    '--id',
    'cluster_id',
    default=None,
    required=False,
    metavar='CLUSTER_ID',
    help="ID of the cluster whose cluster config has to be obtained;"
         "Supported only for CSE api version >= 35."
         "ID gets precedence over cluster name.")
def cluster_delete(ctx, name, vdc, org, k8_runtime=None, cluster_id=None):
    """Delete a Kubernetes cluster.

\b
Example
    vcd cse cluster delete mycluster --yes
        Delete cluster 'mycluster' without prompting.
        '--vdc' option can be used for faster command execution.
\b
    vcd cse cluster delete --id urn:vcloud:entity:cse:nativeCluster:1.0.0:0632c7c7-a613-427c-b4fc-9f1247da5561
        Delete cluster with cluster ID 'urn:vcloud:entity:cse:nativeCluster:1.0.0:0632c7c7-a613-427c-b4fc-9f1247da5561'.
        (--id option is suported only applicable for api version >= 35)
    """  # noqa: E501
    CLIENT_LOGGER.debug(f'Executing command: {ctx.command_path}')
    try:
        client_utils.cse_restore_session(ctx)
        if not (cluster_id or name):
            # --id is not required when working with api version 33 and 34
            raise Exception("Please specify cluster name (or) cluster Id. "
                            "Note that '--id' flag is applicable for API versions >= 35 only.")  # noqa: E501

        client = ctx.obj['client']
        if client_utils.is_cli_for_tkg_only():
            if k8_runtime in [shared_constants.ClusterEntityKind.NATIVE.value,
                              shared_constants.ClusterEntityKind.TKG_PLUS.value]:  # noqa: E501
                # Cannot run the command as cse cli is enabled only for native
                raise CseServerNotRunningError()
            k8_runtime = shared_constants.ClusterEntityKind.TKG.value
        cluster = Cluster(client, k8_runtime=k8_runtime)
        if not client.is_sysadmin() and org is None:
            org = ctx.obj['profiles'].get('org_in_use')
        result = cluster.delete_cluster(name, cluster_id=cluster_id,
                                        org=org, vdc=vdc)
        if len(result) == 0:
            click.secho(f"Delete cluster operation has been initiated on "
                        f"{name}, please check the status using"
                        f" 'vcd cse cluster info {name}'.", fg='yellow')
        stdout(result, ctx)
        CLIENT_LOGGER.debug(result)
    except Exception as e:
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))


@cluster_group.command('create', short_help='Create a Kubernetes cluster')
@click.pass_context
@click.argument('name', required=True)
@click.option(
    '-v',
    '--vdc',
    'vdc',
    required=False,
    default=None,
    metavar='VDC_NAME',
    help='Org VDC to use. Defaults to currently logged-in org VDC')
@click.option(
    '-N',
    '--nodes',
    'node_count',
    required=False,
    default=None,
    type=click.INT,
    help='Number of worker nodes to create')
@click.option(
    '-c',
    '--cpu',
    'cpu',
    required=False,
    default=None,
    type=click.INT,
    help='Number of virtual CPUs on each node')
@click.option(
    '-m',
    '--memory',
    'memory',
    required=False,
    default=None,
    type=click.INT,
    help='Megabytes of memory on each node')
@click.option(
    '-n',
    '--network',
    'network_name',
    default=None,
    required=False,
    help='Org vDC network name (Required)')
@click.option(
    '-s',
    '--storage-profile',
    'storage_profile',
    required=False,
    default=None,
    help='Name of the storage profile for the nodes')
@click.option(
    '-k',
    '--ssh-key',
    'ssh_key_file',
    required=False,
    default=None,
    type=click.File('r'),
    help='SSH public key filepath')
@click.option(
    '-t',
    '--template-name',
    'template_name',
    required=False,
    default=None,
    help='Name of the template to create new nodes from. '
         'If not specified, server default will be used '
         '(Must be used with --template-revision).')
@click.option(
    '-r',
    '--template-revision',
    'template_revision',
    required=False,
    default=None,
    help='Revision number of the template to create new nodes from. '
         'If not specified, server default will be used '
         '(Must be used with --template-revision).')
@click.option(
    '--enable-nfs',
    'enable_nfs',
    is_flag=True,
    help='Create 1 additional NFS node (if --nodes=2, then CSE will create '
         '2 worker nodes and 1 NFS node)')
@click.option(
    '--disable-rollback',
    'disable_rollback',
    is_flag=True,
    help='Disable rollback on cluster creation failure')
@click.option(
    '-o',
    '--org',
    'org_name',
    default=None,
    required=False,
    metavar='ORG_NAME',
    help='Org to use. Defaults to currently logged-in org')
def cluster_create(ctx, name, vdc, node_count, network_name,
                   storage_profile, ssh_key_file, template_name,
                   template_revision, enable_nfs, disable_rollback, org_name,
                   cpu=None, memory=None):
    """Create a Kubernetes cluster (max name length is 25 characters).

\b
Examples
    vcd cse cluster create mycluster --network mynetwork
        Create a Kubernetes cluster named 'mycluster'.
        The cluster will have 2 worker nodes.
        The cluster will be connected to org VDC network 'mynetwork'.
        All VMs will use the default template.
        On create failure, the invalid cluster is deleted.
\b
    vcd cse cluster create mycluster --nodes 1 --enable-nfs \\
    --network mynetwork --template-name photon-v2 --template-revision 1 \\
    --cpu 3 --memory 1024 --storage-profile mystorageprofile \\
    --ssh-key ~/.ssh/id_rsa.pub --disable-rollback --vdc othervdc
        Create a Kubernetes cluster named 'mycluster' on org VDC 'othervdc'.
        The cluster will have 1 worker node and 1 NFS node.
        The cluster will be connected to org VDC network 'mynetwork'.
        All VMs will use the template 'photon-v2'.
        Each VM in the cluster will have 3 vCPUs and 1024mb of memory.
        All VMs will use the storage profile 'mystorageprofile'.
        The public ssh key at '~/.ssh/id_rsa.pub' will be placed into all
        VMs for user accessibility.
        On create failure, cluster will be left cluster in error state for
        troubleshooting.
    """
    CLIENT_LOGGER.debug(f'Executing command: {ctx.command_path}')
    try:
        if (template_name and not template_revision) or \
                (not template_name and template_revision):
            raise Exception("Both flags --template-name(-t) and "
                            "--template-revision (-r) must be specified.")

        client_utils.cse_restore_session(ctx)
        if vdc is None:
            vdc = ctx.obj['profiles'].get('vdc_in_use')
            if not vdc:
                raise Exception("Virtual datacenter context is not set. "
                                "Use either command 'vcd vdc use' or option "
                                "'--vdc' to set the vdc context.")
        if org_name is None:
            org_name = ctx.obj['profiles'].get('org_in_use')
        ssh_key = None
        if ssh_key_file is not None:
            ssh_key = ssh_key_file.read()

        client = ctx.obj['client']
        cluster = Cluster(client)
        result = cluster.create_cluster(
            vdc,
            network_name,
            name,
            node_count=node_count,
            cpu=cpu,
            memory=memory,
            storage_profile=storage_profile,
            ssh_key=ssh_key,
            template_name=template_name,
            template_revision=template_revision,
            enable_nfs=enable_nfs,
            rollback=not disable_rollback,
            org=org_name)
        stdout(result, ctx)
        CLIENT_LOGGER.debug(result)
    except CseResponseError as e:
        minor_error_code_to_error_message = {
            MinorErrorCode.REQUEST_KEY_NETWORK_NAME_MISSING: 'Missing option "-n" / "--network".', # noqa: E501
            MinorErrorCode.REQUEST_KEY_NETWORK_NAME_INVALID: 'Invalid or missing value for option "-n" / "--network".' # noqa: E501
        }
        e.error_message = \
            minor_error_code_to_error_message.get(
                e.minor_error_code, e.error_message)
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))
    except Exception as e:
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))


@cluster_group.command('resize',
                       short_help='Resize the cluster to contain the '
                                  'specified number of worker nodes')
@click.pass_context
@click.argument('cluster_name', required=True)
@click.option(
    '-N',
    '--nodes',
    'node_count',
    required=True,
    default=None,
    type=click.INT,
    help='Desired number of worker nodes for the cluster')
@click.option(
    '-n',
    '--network',
    'network_name',
    default=None,
    required=False,
    help='Network name (Exclusive to native Kubernetes provider) (Required)')
@click.option(
    '-v',
    '--vdc',
    'vdc_name',
    required=False,
    default=None,
    metavar='VDC_NAME',
    help='Restrict cluster search to specified org VDC')
@click.option(
    '-o',
    '--org',
    'org_name',
    default=None,
    required=False,
    metavar='ORG_NAME',
    help='Restrict cluster search to specified org')
@click.option(
    '--disable-rollback',
    'disable_rollback',
    is_flag=True,
    help='Disable rollback on node creation failure '
         '(Exclusive to native Kubernetes provider)')
@click.option(
    '-t',
    '--template-name',
    'template_name',
    required=False,
    default=None,
    help='Name of the template to create new nodes from. '
         'If not specified, server default will be used '
         '(Exclusive to native Kubernetes provider) '
         '(Must be used with --template-revision).')
@click.option(
    '-r',
    '--template-revision',
    'template_revision',
    required=False,
    default=None,
    help='Revision number of the template to create new nodes from. '
         'If not specified, server default will be used '
         '(Exclusive to native Kubernetes provider) '
         '(Must be used with --template-revision).')
@click.option(
    '-c',
    '--cpu',
    'cpu',
    required=False,
    default=None,
    type=click.INT,
    help='Number of virtual CPUs on each node '
         '(Exclusive to native Kubernetes provider)')
@click.option(
    '-m',
    '--memory',
    'memory',
    required=False,
    default=None,
    type=click.INT,
    help='Megabytes of memory on each node '
         '(Exclusive to native Kubernetes provider)')
@click.option(
    '-k',
    '--ssh-key',
    'ssh_key_file',
    required=False,
    default=None,
    type=click.File('r'),
    help='SSH public key filepath (Exclusive to native Kubernetes provider)')
def cluster_resize(ctx, cluster_name, node_count, network_name, org_name,
                   vdc_name, disable_rollback, template_name,
                   template_revision, cpu, memory, ssh_key_file):
    """Resize the cluster to contain the specified number of worker nodes.

    Clusters that use native Kubernetes provider can not be sized down
    (use 'vcd cse node delete' command to do so).
\b
Examples
    vcd cse cluster resize mycluster --nodes 5 --network mynetwork
        Resize the cluster to have 5 worker nodes. On resize failure,
        returns cluster to original size.
        Nodes will be created from server default template at default revision.
        '--vdc' option can be used for faster command execution.
\b
    vcd cse cluster resize mycluster -N 10 --template-name my_template \\
    --template-revision 2 --disable-rollback
        Resize the cluster size to 10 worker nodes. On resize failure,
        cluster will be left cluster in error state for troubleshooting.
        Nodes will be created from template 'my_template' revision 2.
    """
    CLIENT_LOGGER.debug(f'Executing command: {ctx.command_path}')
    try:
        if (template_name and not template_revision) or \
                (not template_name and template_revision):
            raise Exception("Both --template-name (-t) and "
                            "--template-revision (-r) must be specified.")

        client_utils.cse_restore_session(ctx)
        client = ctx.obj['client']
        if not client.is_sysadmin() and org_name is None:
            org_name = ctx.obj['profiles'].get('org_in_use')

        ssh_key = None
        if ssh_key_file:
            ssh_key = ssh_key_file.read()
        cluster = Cluster(client)
        result = cluster.resize_cluster(
            network_name,
            cluster_name,
            node_count=node_count,
            org=org_name,
            vdc=vdc_name,
            rollback=not disable_rollback,
            template_name=template_name,
            template_revision=template_revision,
            cpu=cpu,
            memory=memory,
            ssh_key=ssh_key)
        stdout(result, ctx)
        CLIENT_LOGGER.debug(result)
    except CseResponseError as e:
        minor_error_code_to_error_message = {
            MinorErrorCode.REQUEST_KEY_NETWORK_NAME_MISSING: 'Missing option "-n" / "--network".', # noqa: E501
            MinorErrorCode.REQUEST_KEY_NETWORK_NAME_INVALID: 'Invalid or missing value for option "-n" / "--network".' # noqa: E501
        }
        e.error_message = \
            minor_error_code_to_error_message.get(
                e.minor_error_code, e.error_message)
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))
    except Exception as e:
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))


@cluster_group.command('apply',
                       short_help='apply a configuration to a cluster resource'
                                  ' by filename. The resource will be created '
                                  'if it does not exist.')
@click.pass_context
@click.argument(
    'cluster_config_file_path',
    required=False,
    metavar='CLUSTER_CONFIG_FILE_PATH',
    type=click.Path(exists=True))
@click.option(
    '-s',
    '--sample',
    'generate_sample_config',
    is_flag=True,
    required=False,
    default=False,
    help="generate sample cluster configuration file; This flag can't be used together with CLUSTER_CONFIG_FILE_PATH")  # noqa: E501
@click.option(
    '-n',
    '--native',
    'k8_runtime',
    is_flag=True,
    flag_value=shared_constants.ClusterEntityKind.NATIVE,
    help="should be used with --sample, this flag generates sample yaml for k8 runtime: native"  # noqa: E501
)
@click.option(
    '-t',
    '--tkg',
    'k8_runtime',
    is_flag=True,
    flag_value=shared_constants.ClusterEntityKind.TKG,
    help="should be used with --sample, this flag generates sample yaml for k8 runtime: TKG"  # noqa: E501
)
@click.option(
    '-k',
    '--tkg-plus',
    'k8_runtime',
    is_flag=True,
    hidden=not utils.is_environment_variable_enabled(cli_constants.ENV_CSE_TKG_PLUS_ENABLED),  # noqa: E501
    flag_value=shared_constants.ClusterEntityKind.TKG_PLUS,
    help="should be used with --sample, this flag generates sample yaml for k8 runtime: TKG+"  # noqa: E501
)
@click.option(
    '-o',
    '--output',
    'output',
    required=False,
    default=None,
    metavar='OUTPUT_FILE_NAME',
    help="Filepath to write sample configuration file to; This flag should be used with -s")  # noqa: E501
@click.option(
    '--org',
    'org',
    default=None,
    required=False,
    metavar='ORGANIZATION',
    help="Organization on which the cluster configuration needs to be applied")
@click.option(
    '--id',
    'cluster_id',
    default=None,
    required=False,
    metavar='CLUSTER_ID',
    help="ID of the cluster to which the configuration should be applied;"
         "Supported only for CSE api version >=35."
         "ID gets precedence over cluster name.")
def apply(ctx, cluster_config_file_path, generate_sample_config, k8_runtime, output, org, cluster_id):  # noqa: E501
    CLIENT_LOGGER.debug(f'Executing command: {ctx.command_path}')
    try:
        console_message_printer = utils.ConsoleMessagePrinter()
        if cluster_config_file_path and (generate_sample_config or output or k8_runtime):  # noqa: E501
            console_message_printer.general_no_color(ctx.get_help())
            msg = "-s/-o/-n/-t/-k flag can't be used together with CLUSTER_CONFIG_FILE_PATH"  # noqa: E501
            CLIENT_LOGGER.error(msg)
            raise Exception(msg)

        if not cluster_config_file_path and not generate_sample_config:
            console_message_printer.general_no_color(ctx.get_help())
            msg = "No option chosen/invalid option"
            CLIENT_LOGGER.error(msg)
            raise Exception(msg)

        if generate_sample_config:
            if not k8_runtime:
                console_message_printer.general_no_color(ctx.get_help())
                msg = "with option --sample you must specify either of options: --native or --tkg or --tkg-plus"  # noqa: E501
                CLIENT_LOGGER.error(msg)
                raise Exception(msg)
            elif k8_runtime == shared_constants.ClusterEntityKind.TKG_PLUS \
                    and not utils.is_environment_variable_enabled(cli_constants.ENV_CSE_TKG_PLUS_ENABLED):  # noqa: E501
                raise Exception(f"{shared_constants.ClusterEntityKind.TKG_PLUS.value} not enabled")  # noqa: E501
            else:
                sample_cluster_config = client_sample_generator.get_sample_cluster_configuration(output=output, k8_runtime=k8_runtime)  # noqa: E501
                console_message_printer.general_no_color(sample_cluster_config)
                return

        client = ctx.obj['client']
        with open(cluster_config_file_path) as f:
            cluster_config = yaml.safe_load(f) or {}

        k8_runtime = cluster_config.get('kind')
        if not k8_runtime:
            raise Exception("Cluster kind missing from the spec.")
        if client_utils.is_cli_for_tkg_only():
            if k8_runtime in [shared_constants.ClusterEntityKind.NATIVE.value,
                              shared_constants.ClusterEntityKind.TKG_PLUS.value]:  # noqa: E501
                # Cannot run the command as cse cli is enabled only for native
                raise CseServerNotRunningError()
            k8_runtime = shared_constants.ClusterEntityKind.TKG.value
        org_name = None
        if k8_runtime == shared_constants.ClusterEntityKind.TKG.value:
            org_name = org
            if not org:
                org_name = ctx.obj['profiles'].get('org_in_use')

        cluster = Cluster(client, k8_runtime=cluster_config.get('kind'))  # noqa: E501
        result = cluster.apply(cluster_config, cluster_id=cluster_id,
                               org=org_name)
        stdout(result, ctx)
        CLIENT_LOGGER.debug(result)
    except Exception as e:
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))


@cluster_group.command('delete-nfs',
                       help="Examples:\n\nvcd cse cluster delete-nfs mycluster nfs-uitj",  # noqa: E501
                       short_help='Delete nfs node from Native Kubernetes cluster')  # noqa: E501
@click.pass_context
@click.argument('cluster_name', required=True)
@click.argument('node_name', required=True)
@click.option(
    '-v',
    '--vdc',
    'vdc',
    required=False,
    default=None,
    metavar='VDC_NAME',
    help='Restrict cluster search to specified org VDC')
@click.option(
    '-o',
    '--org',
    'org',
    default=None,
    required=False,
    metavar='ORG_NAME',
    help='Restrict cluster search to specified org')
def delete_nfs(ctx, cluster_name, node_name, vdc, org):
    """Remove nfs node in a cluster that uses native Kubernetes provider."""
    CLIENT_LOGGER.debug(f'Executing command: {ctx.command_path}')
    try:
        client_utils.cse_restore_session(ctx)
        client = ctx.obj['client']
        if not client.is_sysadmin() and org is None:
            org = ctx.obj['profiles'].get('org_in_use')
        cluster = DEClusterNative(client)
        result = cluster.delete_nfs_node(cluster_name, node_name, org=org, vdc=vdc)  # noqa: E501
        stdout(result, ctx)
        CLIENT_LOGGER.debug(result)
    except Exception as e:
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))


@cluster_group.command('upgrade-plan',
                       short_help='Display templates that the specified '
                                  'native cluster can be upgraded to')
@click.pass_context
@click.argument('cluster_name', required=True)
@click.option(
    '-v',
    '--vdc',
    'vdc',
    required=False,
    default=None,
    metavar='VDC_NAME',
    help='Restrict cluster search to specific org VDC')
@click.option(
    '-o',
    '--org',
    'org_name',
    default=None,
    required=False,
    metavar='ORG_NAME',
    help="Restrict cluster search to specific org")
@click.option(
    '-k',
    '--k8-runtime',
    'k8_runtime',
    default=None,
    required=False,
    metavar='K8-RUNTIME',
    help='Restrict cluster search to cluster kind; Supported only '
         'for vcd api version >= 35.')
def cluster_upgrade_plan(ctx, cluster_name, vdc, org_name, k8_runtime=None):
    """Display templates that the specified cluster can upgrade to.

\b
Examples
    vcd cse cluster upgrade-plan my-cluster
    (Supported only for vcd api version < 35)
\b
    vcd cse cluster upgrade-plan --k8-runtime native my-cluster
    (Supported only for vcd api version >= 35)
    """
    CLIENT_LOGGER.debug(f'Executing command: {ctx.command_path}')
    try:
        client_utils.cse_restore_session(ctx)
        if client_utils.is_cli_for_tkg_only():
            if k8_runtime in [shared_constants.ClusterEntityKind.NATIVE.value,
                              shared_constants.ClusterEntityKind.TKG_PLUS.value]:  # noqa: E501
                # Cannot run the command as cse cli is enabled only for native
                raise CseServerNotRunningError()
            k8_runtime = shared_constants.ClusterEntityKind.TKG.value
        client = ctx.obj['client']
        cluster = Cluster(client, k8_runtime=k8_runtime)
        if not client.is_sysadmin() and org_name is None:
            org_name = ctx.obj['profiles'].get('org_in_use')

        templates = cluster.get_upgrade_plan(cluster_name, vdc=vdc,
                                             org=org_name)
        result = []
        for template in templates:
            result.append({
                'Template Name': template[LocalTemplateKey.NAME],
                'Template Revision': template[LocalTemplateKey.REVISION],
                'Kubernetes': template[LocalTemplateKey.KUBERNETES_VERSION],
                'Docker-CE': template[LocalTemplateKey.DOCKER_VERSION],
                'CNI': f"{template[LocalTemplateKey.CNI]} {template[LocalTemplateKey.CNI_VERSION]}" # noqa: E501
            })

        if not templates:
            result = f"No valid upgrade targets for cluster '{cluster_name}'"
        stdout(result, ctx, sort_headers=False)
        CLIENT_LOGGER.debug(result)
    except Exception as e:
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))


@cluster_group.command('upgrade',
                       help="Examples:\n\nvcd cse cluster upgrade my-cluster ubuntu-16.04_k8-1.18_weave-2.6.4 1"  # noqa: E501
                            "\n(Supported only for vcd api version < 35)"
                            "\n\nvcd cse cluster upgrade -k native mcluster photon-v2_k8-1.14_weave-2.5.2 2"  # noqa: E501
                            "\n(Supported only for vcd api version >= 35)",
                       short_help="Upgrade native cluster software to "
                                  "specified template's software versions")
@click.pass_context
@click.argument('cluster_name', required=True)
@click.argument('template_name', required=True)
@click.argument('template_revision', required=True)
@click.option(
    '-v',
    '--vdc',
    'vdc',
    required=False,
    default=None,
    metavar='VDC_NAME',
    help='Restrict cluster search to specific org VDC')
@click.option(
    '-o',
    '--org',
    'org_name',
    default=None,
    required=False,
    metavar='ORG_NAME',
    help="Restrict cluster search to specific org")
@click.option(
    '-k',
    '--k8-runtime',
    'k8_runtime',
    default=None,
    required=False,
    metavar='K8-RUNTIME',
    help='Restrict cluster search to cluster kind; Supported '
         'only for vcd api version >= 35.')
def cluster_upgrade(ctx, cluster_name, template_name, template_revision,
                    vdc, org_name, k8_runtime=None):
    """Upgrade cluster software to specified template's software versions.

\b
Example
    vcd cse cluster upgrade my-cluster ubuntu-16.04_k8-1.18_weave-2.6.4 1
        Upgrade cluster 'mycluster' Docker-CE, Kubernetes, and CNI to match
        template 'ubuntu-16.04_k8-1.18_weave-2.6.4' at revision 1.
        Affected software: Docker-CE, Kubernetes, CNI
    """
    CLIENT_LOGGER.debug(f'Executing command: {ctx.command_path}')
    try:
        client_utils.cse_restore_session(ctx)
        if client_utils.is_cli_for_tkg_only():
            if k8_runtime in [shared_constants.ClusterEntityKind.NATIVE.value,
                              shared_constants.ClusterEntityKind.TKG_PLUS.value]:  # noqa: E501
                # Cannot run the command as cse cli is enabled only for native
                raise CseServerNotRunningError()
            k8_runtime = shared_constants.ClusterEntityKind.TKG.value
        client = ctx.obj['client']
        cluster = Cluster(client, k8_runtime=k8_runtime)
        if not client.is_sysadmin() and org_name is None:
            org_name = ctx.obj['profiles'].get('org_in_use')

        result = cluster.upgrade_cluster(cluster_name, template_name,
                                         template_revision, ovdc_name=vdc,
                                         org_name=org_name)
        stdout(result, ctx)
        CLIENT_LOGGER.debug(result)
    except Exception as e:
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))


@cluster_group.command('config',
                       short_help='Retrieve cluster configuration details')
@click.pass_context
@click.argument('name', default=None, required=False)
@click.option(
    '-o',
    '--org',
    'org',
    required=False,
    default=None,
    metavar='ORG_NAME',
    help='Restrict cluster search to specified org')
@click.option(
    '-v',
    '--vdc',
    'vdc',
    required=False,
    default=None,
    metavar='VDC_NAME',
    help='Restrict cluster search to specified org VDC')
@click.option(
    '-k',
    '--k8-runtime',
    'k8_runtime',
    default=None,
    required=False,
    metavar='K8-RUNTIME',
    help='Restrict cluster search to cluster kind;'
         'Supported only for vcd api version >= 35')
@click.option(
    '--id',
    'cluster_id',
    default=None,
    required=False,
    metavar='CLUSTER_ID',
    help="ID of the cluster whose cluster config has to be obtained."
         "Supported only for CSE api version >= 35."
         "ID gets precedence over cluster name.")
def cluster_config(ctx, name, vdc, org, k8_runtime=None, cluster_id=None):
    """Display cluster configuration.

\b
Examples:
    vcd cse cluster config my-cluster
    (Supported only for vcd api version < 35)
\b
    vcd cse cluster config -k native my-cluster
    (Supported only for vcd api version >= 35)

    To write to a file: `vcd cse cluster config mycluster > ~/.kube/my_config`
\b
    vcd cse cluster config --id urn:vcloud:entity:cse:nativeCluster:1.0.0:0632c7c7-a613-427c-b4fc-9f1247da5561
    (--id option is supported only for vcd api version >= 35)
    """  # noqa: E501
    CLIENT_LOGGER.debug(f'Executing command: {ctx.command_path}')
    try:
        if not (cluster_id or name):
            # --id is not required when working with api version 33 and 34
            raise Exception("Please specify cluster name (or) cluster Id. "
                            "Note that '--id' flag is applicable for API versions >= 35 only.")  # noqa: E501
        client_utils.cse_restore_session(ctx)
        if client_utils.is_cli_for_tkg_only():
            if k8_runtime in [shared_constants.ClusterEntityKind.NATIVE.value,
                              shared_constants.ClusterEntityKind.TKG_PLUS.value]:  # noqa: E501
                # Cannot run the command as cse cli is enabled only for native
                raise CseServerNotRunningError()
            k8_runtime = shared_constants.ClusterEntityKind.TKG.value
        client = ctx.obj['client']
        cluster = Cluster(client, k8_runtime=k8_runtime)
        if not client.is_sysadmin() and org is None:
            org = ctx.obj['profiles'].get('org_in_use')
        cluster_config = \
            cluster.get_cluster_config(name, cluster_id=cluster_id,
                                       vdc=vdc, org=org) \
            .get(shared_constants.RESPONSE_MESSAGE_KEY)  # noqa: E501
        if os.name == 'nt':
            cluster_config = str.replace(cluster_config, '\n', '\r\n')

        click.secho(cluster_config)
        CLIENT_LOGGER.debug(cluster_config)
    except Exception as e:
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))


@cluster_group.command('info',
                       short_help='Display info about a cluster')
@click.pass_context
@click.argument('name', default=None, required=False)
@click.option(
    '-v',
    '--vdc',
    'vdc',
    required=False,
    default=None,
    metavar='VDC_NAME',
    help='Restrict cluster search to specified org VDC')
@click.option(
    '-o',
    '--org',
    'org',
    default=None,
    required=False,
    metavar='ORG_NAME',
    help='Restrict cluster search to specified org')
@click.option(
    '-k',
    '--k8-runtime',
    'k8_runtime',
    default=None,
    required=False,
    metavar='K8-RUNTIME',
    help='Restrict cluster search to cluster kind;'
         'Supported only for vcd api version >=35')
@click.option(
    '--id',
    'cluster_id',
    default=None,
    required=False,
    metavar='CLUSTER_ID',
    help="ID of the cluster whose cluster config has to be obtained;"
         "Supported only for CSE api version >=35. "
         "ID gets precedence over cluster name.")
def cluster_info(ctx, name, org, vdc, k8_runtime=None, cluster_id=None):
    """Display info about a Kubernetes cluster.

\b
Example
    vcd cse cluster info mycluster
        Display detailed information about cluster 'mycluster'.
        '--vdc' option can be used for faster command execution.
\b
    vcd cse cluster info --id urn:vcloud:entity:cse:nativeCluster:1.0.0:0632c7c7-a613-427c-b4fc-9f1247da5561
        Display cluster information about cluster with
        ID 'urn:vcloud:entity:cse:nativeCluster:1.0.0:0632c7c7-a613-427c-b4fc-9f1247da5561'
        (--id option is supported only for api version >= 35)
    """  # noqa: E501
    CLIENT_LOGGER.debug(f'Executing command: {ctx.command_path}')
    try:
        if not (cluster_id or name):
            # --id is not required when working with api version 33 and 34
            raise Exception("Please specify cluster name (or) cluster Id. "
                            "Note that '--id' flag is applicable for API versions >= 35 only.")  # noqa: E501
        client_utils.cse_restore_session(ctx)
        if client_utils.is_cli_for_tkg_only():
            if k8_runtime in [shared_constants.ClusterEntityKind.NATIVE.value,
                              shared_constants.ClusterEntityKind.TKG_PLUS.value]:  # noqa: E501
                # Cannot run the command as cse cli is enabled only for native
                raise CseServerNotRunningError()
            k8_runtime = shared_constants.ClusterEntityKind.TKG.value
        client = ctx.obj['client']
        cluster = Cluster(client, k8_runtime=k8_runtime)
        if not client.is_sysadmin() and org is None:
            org = ctx.obj['profiles'].get('org_in_use')
        result = cluster.get_cluster_info(name, cluster_id=cluster_id,
                                          org=org, vdc=vdc)
        stdout(result, ctx)
        CLIENT_LOGGER.debug(result)
    except Exception as e:
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))


@cse.group('node', short_help='Manage nodes of native clusters')
@click.pass_context
def node_group(ctx):
    """Manage nodes of native clusters.

These commands will only work with clusters created by native
Kubernetes runtime.
    """
    pass


@node_group.command('info',
                    short_help='Display info about a node in a cluster that '
                               'was created with native Kubernetes provider')
@click.pass_context
@click.argument('cluster_name', required=True)
@click.argument('node_name', required=True)
@click.option(
    '-o',
    '--org',
    'org_name',
    default=None,
    required=False,
    metavar='ORG_NAME',
    help='Restrict cluster search to specified org')
@click.option(
    '-v',
    '--vdc',
    'vdc',
    required=False,
    default=None,
    metavar='VDC_NAME',
    help='Restrict cluster search to specified org VDC')
def node_info(ctx, cluster_name, node_name, org_name, vdc):
    """Display info about a node in a native Kubernetes provider cluster.

\b
Example
    vcd cse node info mycluster node-xxxx
        Display detailed information about node 'node-xxxx' in cluster
        'mycluster'.
    """
    CLIENT_LOGGER.debug(f'Executing command: {ctx.command_path}')
    try:
        client_utils.cse_restore_session(ctx)
        client = ctx.obj['client']
        cluster = Cluster(client)

        if org_name is None and not client.is_sysadmin():
            org_name = ctx.obj['profiles'].get('org_in_use')
        node_info = cluster.get_node_info(cluster_name, node_name,
                                          org_name, vdc)
        value_field_to_display_field = {
            'name': 'Name',
            'node_type': 'Node Type',
            'ipAddress': 'IP Address',
            'numberOfCpus': 'Number of CPUs',
            'memoryMB': 'Memory MB',
            'status': 'Status'
        }
        filtered_node_info = client_utils.filter_columns(
            node_info, value_field_to_display_field)
        stdout(filtered_node_info, ctx, sort_headers=False)
        CLIENT_LOGGER.debug(filtered_node_info)
    except Exception as e:
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))


@node_group.command('create',
                    short_help='Add node(s) to a cluster that was created '
                               'with native Kubernetes provider')
@click.pass_context
@click.argument('cluster_name', required=True)
@click.option(
    '-N',
    '--nodes',
    'node_count',
    required=False,
    default=1,
    type=click.INT,
    help='Number of nodes to create')
@click.option(
    '-c',
    '--cpu',
    'cpu',
    required=False,
    default=None,
    type=click.INT,
    help='Number of virtual CPUs on each node')
@click.option(
    '-m',
    '--memory',
    'memory',
    required=False,
    default=None,
    type=click.INT,
    help='Megabytes of memory on each node')
@click.option(
    '-n',
    '--network',
    'network_name',
    default=None,
    required=True,
    help='Network name')
@click.option(
    '-s',
    '--storage-profile',
    'storage_profile',
    required=False,
    default=None,
    help='Name of the storage profile for the nodes')
@click.option(
    '-k',
    '--ssh-key',
    'ssh_key_file',
    required=False,
    default=None,
    type=click.File('r'),
    help='SSH public key to connect to the guest OS on the VM')
@click.option(
    '-t',
    '--template-name',
    'template_name',
    required=False,
    default=None,
    help='Name of the template to create new nodes from. '
         'If not specified, server default will be used '
         '(Must be used with --template-revision).')
@click.option(
    '-r',
    '--template-revision',
    'template_revision',
    required=False,
    default=None,
    help='Revision number of the template to create new nodes from. '
         'If not specified, server default will be used '
         '(Must be used with --template-revision).')
@click.option(
    '--enable-nfs',
    'enable_nfs',
    is_flag=True,
    help='Enable NFS on all created nodes')
@click.option(
    '--disable-rollback',
    'disable_rollback',
    is_flag=True,
    help='Disable rollback on node deployment failure')
@click.option(
    '-v',
    '--vdc',
    'vdc',
    required=False,
    default=None,
    metavar='VDC_NAME',
    help='Restrict cluster search to specified org VDC')
@click.option(
    '-o',
    '--org',
    'org',
    default=None,
    required=False,
    metavar='ORG_NAME',
    help='Restrict cluster search to specified org')
def create_node(ctx, cluster_name, node_count, org, vdc, cpu, memory,
                network_name, storage_profile, ssh_key_file, template_name,
                template_revision, enable_nfs, disable_rollback):
    """Add node(s) to a cluster that uses native Kubernetes provider.

\b
Example
    vcd cse node create mycluster --nodes 2 --enable-nfs --network mynetwork \\
    --template-name photon-v2 --template-revision 1 --cpu 3 --memory 1024 \\
    --storage-profile mystorageprofile --ssh-key ~/.ssh/id_rsa.pub \\
        Add 2 nfs nodes to vApp named 'mycluster' on vCD.
        The nodes will be connected to org VDC network 'mynetwork'.
        All VMs will use the template 'photon-v2'.
        Each VM will have 3 vCPUs and 1024mb of memory.
        All VMs will use the storage profile 'mystorageprofile'.
        The public ssh key at '~/.ssh/id_rsa.pub' will be placed into all
        VMs for user accessibility.

    """
    CLIENT_LOGGER.debug(f'Executing command: {ctx.command_path}')
    try:
        if (template_name and not template_revision) or \
                (not template_name and template_revision):
            raise Exception("Both --template-name (-t) and "
                            "--template-revision (-r) must be specified.")

        client_utils.cse_restore_session(ctx)
        client = ctx.obj['client']
        if org is None and not client.is_sysadmin():
            org = ctx.obj['profiles'].get('org_in_use')
        cluster = Cluster(client)
        ssh_key = None
        if ssh_key_file is not None:
            ssh_key = ssh_key_file.read()
        result = cluster.add_node(
            network_name,
            cluster_name,
            node_count=node_count,
            org=org,
            vdc=vdc,
            cpu=cpu,
            memory=memory,
            storage_profile=storage_profile,
            ssh_key=ssh_key,
            template_name=template_name,
            template_revision=template_revision,
            enable_nfs=enable_nfs,
            rollback=not disable_rollback)
        stdout(result, ctx)
        CLIENT_LOGGER.debug(result)
    except Exception as e:
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))


@node_group.command('list',
                    short_help='Display nodes of a cluster that was created '
                               'with native Kubernetes provider')
@click.pass_context
@click.argument('name', required=True)
@click.option(
    '-o',
    '--org',
    'org',
    default=None,
    required=False,
    metavar='ORG_NAME',
    help='Restrict cluster search to specified org')
@click.option(
    '-v',
    '--vdc',
    'vdc',
    required=False,
    default=None,
    metavar='VDC_NAME',
    help='Restrict cluster search to specified org VDC')
def list_nodes(ctx, name, org, vdc):
    """Display nodes of a cluster that uses native Kubernetes provider.

\b
Example
    vcd cse node list mycluster
        Displays nodes in 'mycluster'.

    """
    CLIENT_LOGGER.debug(f'Executing command: {ctx.command_path}')
    try:
        client_utils.cse_restore_session(ctx)
        client = ctx.obj['client']
        if org is None and not client.is_sysadmin():
            org = ctx.obj['profiles'].get('org_in_use')
        cluster = Cluster(client)
        cluster_info = cluster.get_cluster_info(name, org=org, vdc=vdc)
        if cluster_info.get(K8S_PROVIDER_KEY) != K8sProvider.NATIVE:
            raise Exception("'node list' operation is not supported by non "
                            "native clusters.")
        all_nodes = cluster_info['master_nodes'] + cluster_info['nodes']
        value_field_to_display_field = {
            'name': 'Name',
            'ipAddress': 'IP Address',
            'numberOfCpus': 'Number of CPUs',
            'memoryMB': 'Memory MB'
        }
        filtered_nodes = client_utils.filter_columns(all_nodes, value_field_to_display_field)  # noqa: E501
        stdout(filtered_nodes, ctx, show_id=True, sort_headers=False)
        CLIENT_LOGGER.debug(all_nodes)
    except Exception as e:
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))


@node_group.command('delete',
                    short_help='Delete node(s) in a cluster that was created '
                               'with native Kubernetes provider')
@click.pass_context
@click.argument('cluster_name', required=True)
@click.argument('node_names', nargs=-1, required=True)
@click.confirmation_option(prompt='Are you sure you want to delete '
                                  'the node(s)?')
@click.option(
    '-v',
    '--vdc',
    'vdc',
    required=False,
    default=None,
    metavar='VDC_NAME',
    help='Restrict cluster search to specified org VDC')
@click.option(
    '-o',
    '--org',
    'org',
    default=None,
    required=False,
    metavar='ORG_NAME',
    help='Restrict cluster search to specified org')
def delete_nodes(ctx, cluster_name, node_names, org, vdc):
    """Delete node(s) in a cluster that uses native Kubernetes provider.

\b
Example
    vcd cse node delete mycluster node-xxxx --yes
        Delete node 'node-xxxx' in cluster 'mycluster' without prompting.
    """
    CLIENT_LOGGER.debug(f'Executing command: {ctx.command_path}')
    try:
        client_utils.cse_restore_session(ctx)
        client = ctx.obj['client']
        if not client.is_sysadmin() and org is None:
            org = ctx.obj['profiles'].get('org_in_use')
        cluster = Cluster(client)
        result = cluster.delete_nodes(cluster_name, list(node_names), org=org,
                                      vdc=vdc)
        stdout(result, ctx)
        CLIENT_LOGGER.debug(result)
    except Exception as e:
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))


@cse.group('system', short_help='Manage CSE service (system daemon)')
@click.pass_context
def system_group(ctx):
    """Manage CSE server remotely.

\b
Examples
    vcd cse system info
        Display detailed information of the CSE server.
\b
    vcd cse system enable --yes
        Enable CSE server without prompting.
\b
    vcd cse system stop --yes
        Stop CSE server without prompting.
\b
    vcd cse system disable --yes
        Disable CSE server without prompting.
    """
    pass


@system_group.command('info', short_help='Display info of CSE server')
@click.pass_context
def system_info(ctx):
    """Display CSE server info."""
    CLIENT_LOGGER.debug(f'Executing command: {ctx.command_path}')
    try:
        client_utils.cse_restore_session(ctx)
        client = ctx.obj['client']
        system = System(client)
        result = system.get_info()
        stdout(result, ctx)
        CLIENT_LOGGER.debug(result)
    except Exception as e:
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))


@system_group.command('stop', short_help='Gracefully stop CSE server')
@click.pass_context
@click.confirmation_option(prompt='Are you sure you want to stop the server?')
def stop_service(ctx):
    """Stop CSE server."""
    CLIENT_LOGGER.debug(f'Executing command: {ctx.command_path}')
    try:
        client_utils.cse_restore_session(ctx)
        client = ctx.obj['client']
        system = System(client)
        result = system.update_service_status(action=shared_constants.ServerAction.STOP) # noqa: E501
        stdout(result, ctx)
        CLIENT_LOGGER.debug(result)
    except Exception as e:
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))


@system_group.command('enable', short_help='Enable CSE server')
@click.pass_context
def enable_service(ctx):
    """Enable CSE server."""
    CLIENT_LOGGER.debug(f'Executing command: {ctx.command_path}')
    try:
        client_utils.cse_restore_session(ctx)
        client = ctx.obj['client']
        system = System(client)
        result = system.update_service_status(action=shared_constants.ServerAction.ENABLE) # noqa: E501
        stdout(result, ctx)
        CLIENT_LOGGER.debug(result)
    except Exception as e:
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))


@system_group.command('disable', short_help='Disable CSE server')
@click.pass_context
def disable_service(ctx):
    """Disable CSE server."""
    CLIENT_LOGGER.debug(f'Executing command: {ctx.command_path}')
    try:
        client_utils.cse_restore_session(ctx)
        client = ctx.obj['client']
        system = System(client)
        result = system.update_service_status(action=shared_constants.ServerAction.DISABLE) # noqa: E501
        stdout(result, ctx)
        CLIENT_LOGGER.debug(result)
    except Exception as e:
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))


@cse.group('ovdc', cls=cmd_filter.GroupCommandFilter,
           short_help='Manage ovdc enablement for native clusters')
@click.pass_context
def ovdc_group(ctx):
    """Manage ovdc enablement for native clusters.

All commands execute in the context of user's currently logged-in
organization. Use a different organization by using the '--org' option.
    """
    pass


@ovdc_group.command('list',
                    short_help='Display org VDCs in vCD that are visible '
                               'to the logged in user')
@click.pass_context
def list_ovdcs(ctx):
    """Display org VDCs in vCD that are visible to the logged in user.

\b
Example
    vcd cse ovdc list
        Display ovdcs in vCD that are visible to the logged in user.
        vcd cse ovdc list
    """
    CLIENT_LOGGER.debug(f'Executing command: {ctx.command_path}')
    try:
        client_utils.cse_restore_session(ctx)
        client = ctx.obj['client']
        ovdc = Ovdc(client)
        result = ovdc.list_ovdc()
        stdout(result, ctx, sort_headers=False)
        CLIENT_LOGGER.debug(result)
    except Exception as e:
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))


@ovdc_group.command('enable',
                    short_help='Enable ovdc for native cluster deployments')
@click.pass_context
@click.argument('ovdc_name', required=True, metavar='VDC_NAME')
@click.option(
    '-o',
    '--org',
    'org_name',
    default=None,
    required=False,
    metavar='ORG_NAME',
    help="Org to use. Defaults to currently logged-in org")
@click.option(
    '-n',
    '--native',
    'enable_native',
    is_flag=True,
    help="Enable OVDC for k8 runtime native"
)
@click.option(
    '-t',
    '--tkg-plus',
    'enable_tkg_plus',
    is_flag=True,
    hidden=not utils.is_environment_variable_enabled(cli_constants.ENV_CSE_TKG_PLUS_ENABLED),  # noqa: E501
    help="Enable OVDC for k8 runtime TKG plus"
)
def ovdc_enable(ctx, ovdc_name, org_name, enable_native, enable_tkg_plus=None):
    """Set Kubernetes provider for an org VDC.

\b
Example
    vcd cse ovdc enable --native --org org1 ovdc1
        Enable native cluster deployment in ovdc1 of org1.
        Supported only for vcd api version >= 35.
\b
    vcd cse ovdc enable ovdc1
        Enable ovdc1 for native cluster deployment.
        Supported only for vcd api version < 35.
    """
    CLIENT_LOGGER.debug(f'Executing command: {ctx.command_path}')
    if not (enable_native or enable_tkg_plus):
        msg = "Please specify at least one k8 runtime to enable"
        stderr(msg, ctx)
        CLIENT_LOGGER.error(msg)
    k8_runtime = []
    if enable_native:
        k8_runtime.append(shared_constants.ClusterEntityKind.NATIVE.value)
    if enable_tkg_plus:
        k8_runtime.append(shared_constants.ClusterEntityKind.TKG_PLUS.value)
    try:
        client_utils.cse_restore_session(ctx)
        client = ctx.obj['client']
        if client.is_sysadmin():
            ovdc = Ovdc(client)
            if org_name is None:
                org_name = ctx.obj['profiles'].get('org_in_use')
            result = ovdc.update_ovdc(
                enable=True,
                ovdc_name=ovdc_name,
                org_name=org_name,
                k8s_runtime=k8_runtime)
            stdout(result, ctx)
            CLIENT_LOGGER.debug(result)
        else:
            msg = "Insufficient permission to perform operation."
            stderr(msg, ctx)
            CLIENT_LOGGER.error(msg)
    except Exception as e:
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))


@ovdc_group.command('disable',
                    short_help='Disable further native cluster deployments on '
                               'the ovdc')
@click.pass_context
@click.argument('ovdc_name', required=True, metavar='VDC_NAME')
@click.option(
    '-o',
    '--org',
    'org_name',
    default=None,
    required=False,
    metavar='ORG_NAME',
    help="Org to use. Defaults to currently logged-in org")
@click.option(
    '-n',
    '--native',
    'disable_native',
    is_flag=True,
    help="Disable OVDC for k8 runtime native cluster"
)
@click.option(
    '-t',
    '--tkg-plus',
    'disable_tkg_plus',
    is_flag=True,
    hidden=not utils.is_environment_variable_enabled(cli_constants.ENV_CSE_TKG_PLUS_ENABLED),  # noqa: E501
    help="Disable OVDC for k8 runtime TKG plus"
)
@click.option(
    '-f',
    '--force',
    'remove_cp_from_vms_on_disable',
    is_flag=True,
    help="Remove the compute policies from deployed VMs as well. "
         "Does not remove the compute policy from vApp templates in catalog. ")
def ovdc_disable(ctx, ovdc_name, org_name,
                 disable_native, disable_tkg_plus=None,
                 remove_cp_from_vms_on_disable=False):
    """Disable Kubernetes cluster deployment for an org VDC.

\b
Examples
    vcd cse ovdc disable --native --org org1 ovdc1
        Disable native cluster deployment in ovdc1 of org1.
        Supported only for vcd api version >= 35.
\b
    vcd cse ovdc disable --native --org org1 --force ovdc1
        Force disable native cluster deployment in ovdc1 of org1.
        Replaces CSE policies with VCD default policies.
        Supported only for vcd api version >= 35.
\b
    vcd cse ovdc disable ovdc3
        Disable ovdc3 for any further native cluster deployments.
        Supported only for vcd api version < 35.

    """
    CLIENT_LOGGER.debug(f'Executing command: {ctx.command_path}')
    if not (disable_native or disable_tkg_plus):
        msg = "Please specify at least one k8 runtime to disable"
        stderr(msg, ctx)
        CLIENT_LOGGER.error(msg)
    k8_runtime = []
    if disable_native:
        k8_runtime.append(shared_constants.ClusterEntityKind.NATIVE.value)
    if disable_tkg_plus:
        k8_runtime.append(shared_constants.ClusterEntityKind.TKG_PLUS.value)
    try:
        client_utils.cse_restore_session(ctx)
        client = ctx.obj['client']
        if client.is_sysadmin():
            ovdc = Ovdc(client)
            if org_name is None:
                org_name = ctx.obj['profiles'].get('org_in_use')
            result = ovdc.update_ovdc(enable=False,
                                      ovdc_name=ovdc_name,
                                      org_name=org_name,
                                      k8s_runtime=k8_runtime,
                                      remove_cp_from_vms_on_disable=remove_cp_from_vms_on_disable) # noqa: E501
            stdout(result, ctx)
            CLIENT_LOGGER.debug(result)
        else:
            msg = "Insufficient permission to perform operation."
            stderr(msg, ctx)
            CLIENT_LOGGER.error(msg)
    except Exception as e:
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))


@ovdc_group.command('info',
                    short_help='Display information about Kubernetes provider '
                               'for an org VDC')
@click.pass_context
@click.argument('ovdc_name', required=True, metavar='VDC_NAME')
@click.option(
    '-o',
    '--org',
    'org_name',
    default=None,
    required=False,
    metavar='ORG_NAME',
    help="Org to use. Defaults to currently logged-in org")
def ovdc_info(ctx, ovdc_name, org_name):
    """Display information about Kubernetes provider for an org VDC.

\b
Example
    vcd cse ovdc info ovdc1
        Display detailed information about ovdc 'ovdc1'.

    """
    CLIENT_LOGGER.debug(f'Executing command: {ctx.command_path}')
    try:
        client_utils.cse_restore_session(ctx)
        client = ctx.obj['client']
        if client.is_sysadmin():
            ovdc = Ovdc(client)
            if org_name is None:
                org_name = ctx.obj['profiles'].get('org_in_use')
            result = ovdc.info_ovdc(ovdc_name, org_name)
            stdout(yaml.dump(result), ctx)
            CLIENT_LOGGER.debug(result)
        else:
            msg = "Insufficient permission to perform operation"
            stderr(msg, ctx)
            CLIENT_LOGGER.error(msg)
    except Exception as e:
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))


@ovdc_group.group('compute-policy',
                  short_help='Manage compute policies for an org VDC')
@click.pass_context
def compute_policy_group(ctx):
    """Manage compute policies for org VDCs.

System administrator operations.

\b
Examples
    vcd cse ovdc compute-policy list --org ORG_NAME --vdc VDC_NAME
        List all compute policies for a specific ovdc in a specific org.
\b
    vcd cse ovdc compute-policy add POLICY_NAME --org ORG_NAME --vdc VDC_NAME
        Add a compute policy to a specific ovdc in a specific org.
\b
    vcd cse ovdc compute-policy remove POLICY_NAME --org ORG_NAME --vdc VDC_NAME
        Remove a compute policy from a specific ovdc in a specific org.
    """ # noqa: E501
    pass


@compute_policy_group.command('list', short_help='')
@click.pass_context
@click.option(
    '-o',
    '--org',
    'org_name',
    metavar='ORG_NAME',
    required=True,
    help="(Required) Org to use")
@click.option(
    '-v',
    '--vdc',
    'ovdc_name',
    metavar='VDC_NAME',
    required=True,
    help="(Required) Org VDC to use")
def compute_policy_list(ctx, org_name, ovdc_name):
    CLIENT_LOGGER.debug(f'Executing command: {ctx.command_path}')
    try:
        client_utils.cse_restore_session(ctx)
        client = ctx.obj['client']
        if not client.is_sysadmin():
            raise Exception("Insufficient permission to perform operation.")

        ovdc = Ovdc(client)
        result = ovdc.list_ovdc_compute_policies(ovdc_name, org_name)
        stdout(result, ctx)
        CLIENT_LOGGER.debug(result)
    except Exception as e:
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))


@compute_policy_group.command('add', short_help='')
@click.pass_context
@click.argument('compute_policy_name', metavar='COMPUTE_POLICY_NAME')
@click.option(
    '-o',
    '--org',
    'org_name',
    metavar='ORG_NAME',
    required=True,
    help="(Required) Org to use")
@click.option(
    '-v',
    '--vdc',
    'ovdc_name',
    metavar='VDC_NAME',
    required=True,
    help="(Required) Org VDC to use")
def compute_policy_add(ctx, org_name, ovdc_name, compute_policy_name):
    CLIENT_LOGGER.debug(f'Executing command: {ctx.command_path}')
    try:
        client_utils.cse_restore_session(ctx)
        client = ctx.obj['client']
        if not client.is_sysadmin():
            raise Exception("Insufficient permission to perform operation.")

        ovdc = Ovdc(client)
        result = ovdc.update_ovdc_compute_policies(ovdc_name,
                                                   org_name,
                                                   compute_policy_name,
                                                   shared_constants.ComputePolicyAction.ADD, # noqa: E501
                                                   False)
        stdout(result, ctx)
        CLIENT_LOGGER.debug(result)
    except Exception as e:
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))


@compute_policy_group.command('remove', short_help='')
@click.pass_context
@click.argument('compute_policy_name', metavar='COMPUTE_POLICY_NAME')
@click.option(
    '-o',
    '--org',
    'org_name',
    metavar='ORG_NAME',
    required=True,
    help="(Required) Org to use")
@click.option(
    '-v',
    '--vdc',
    'ovdc_name',
    metavar='VDC_NAME',
    required=True,
    help="(Required) Org VDC to use")
@click.option(
    '-f',
    '--force',
    'remove_compute_policy_from_vms',
    is_flag=True,
    help="Remove the specified compute policy from deployed VMs as well. "
         "Affected VMs will have 'System Default' compute policy. "
         "Does not remove the compute policy from vApp templates in catalog. "
         "This VM compute policy update is irreversible.")
def compute_policy_remove(ctx, org_name, ovdc_name, compute_policy_name,
                          remove_compute_policy_from_vms):
    CLIENT_LOGGER.debug(f'Executing command: {ctx.command_path}')
    try:
        client_utils.cse_restore_session(ctx)
        client = ctx.obj['client']
        if not client.is_sysadmin():
            raise Exception("Insufficient permission to perform operation.")

        ovdc = Ovdc(client)
        result = ovdc.update_ovdc_compute_policies(ovdc_name,
                                                   org_name,
                                                   compute_policy_name,
                                                   shared_constants.ComputePolicyAction.REMOVE, # noqa: E501
                                                   remove_compute_policy_from_vms) # noqa: E501
        stdout(result, ctx)
        CLIENT_LOGGER.debug(result)
    except Exception as e:
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))


# Add-on CLI support for PKS container provider
cse.add_command(pks.pks_group)
