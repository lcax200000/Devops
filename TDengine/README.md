This project manages virtual machines through Vagrant, creates TDengine master nodes using Ansible, and adds node nodes to the cluster.
Prepare
1. Ensure the SSH connectivity between the Ansible control node and the target node.
2. Ansible controls the host information of the controlled node in the /etc/hosts and /etc/ansible/hosts.
3. Modify the "host" value in the first row of deploy_master.yaml to be the host name of the controlled node.
4. Configure the TDengine template file resources/config/tempdelete.conf as needed, and add the TDengine configuration items that need to be changed to the file (such as whether to turn on monitoring, the fqdn of the monitoring cluster, listening ports, etc.). Ansible will be replaced in the TDengine configuration file during deployment. For TDengine configuration parameters, please refer to: https://docs.taosdata.com/reference/config.

Start virtual machine:
vagrant up

Create cluster:
ansible playbook deploy_master.yaml

Join remote nodes to the cluster:
ansible playbook add_nodes.yaml

Collect local performance and write it to TDengine:
1. Create a data table: python3 scripts/collect_performance/createTable.py.
2. Collect data and write it every 3 seconds to: python3 scripts/collect_performance/collecting.py.

Grafana configuration:
1. Browser opening: http://master IP: 3000, Grafana initial user: admin, password: admin.
2. Select "Data sources" from the left function list and select "tdengine-datasource".
3. Fill in "TDengine Host" http://127.0.0.1:6041. In "TDengine Authentication", enter the username: root and password: taosdata.
4. After Save&test, the message "TDengine Data source is working" pops up, and the TDengine data source import is completed.

Import dashboard:
1. Select Dashboards from the left function list.
2. Select "New" in the upper right corner and select "Import" from the drop-down menu.
3. Upload grafana-dashboard.json, select TDengine datasource as the data source, and import is complete.
