

*This project manages virtual machines through Vagrant, creates TDengine master nodes using Ansible, and adds node nodes to the cluster.* 

## Prepare

1. Ensure the SSH connectivity between the Ansible control node and the target node.
2. Ansible controls the host information of the controlled node in the /etc/hosts and /etc/ansible/hosts.
3. Modify the "host" value in the first row of deploy_master.yaml to be the host name of the controlled node.
4. Configure the TDengine template file resources/config/tempdelete.conf as needed, and add the TDengine configuration items that need to be changed to the file (such as whether to turn on monitoring, the fqdn of the monitoring cluster, listening ports, etc.). Ansible will be replaced in the TDengine configuration file during deployment. For TDengine configuration parameters, please refer to: https://docs.taosdata.com/reference/config.

## How to use

1. Start virtual machine：
   ```
   vagrant up
   ```

2. Create cluster：
   ```
   ansible-playbook deploy_master.yaml
   ```

3. Join remote nodes to the cluster：
   ```
   ansible-playbook add_nodes.yaml
   ```

4. Collect local performance and write it to TDengine：
   - Create a data table： 
     ```
     python3 scripts/collect_performance/create_table.py
     ```
   - Collect data and write it every 3 seconds.
     *The first parameter after it is uid to distinguish different devices, such as collecting data with uid 1*
     ```
     python3 scripts/collect_performance/collecting.py 1
     ```

5. Grafana configuration：
   - Browser opening: `http://master IP: 3000`, Grafana initial user: `admin`, password: `admin`
   - Select `Data sources` from the left function list and select `tdengine-datasource`.
   - Fill in `TDengine Host`: http://127.0.0.1:6041. In `TDengine Authentication`, enter the username: root and password: taosdata.
   - After `Save&test`, the message `TDengine Data source is working` pops up, and the TDengine data source import is completed.

6. Import dashboard：
   - Select Dashboards from the left function list.
   - Select `New` in the upper right corner and select `Import` from the drop-down menu.
   - Upload grafana-dashboard.json, select TDengine datasource as the data source, and import is complete.
