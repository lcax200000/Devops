

*本项目通过使用Vagrant管理虚拟机，利用Ansible创建TDengine的master节点并添加node节点进入集群。*

## 准备工作

1. 在ansible控制节点的本地 `/etc/hosts` 文件中包含被控节点的主机信息。
2. 修改`resources/config/hosts`，其中`[tdengine_master]`下存放master节点的hostname，`[tdengine_nodes]`组下存放其他节点的hostname。
3. 根据需要配置TDengine模板文件 `resources/config/tempelete_conf`，将需要更改的TDengine配置项添加到文件中（例如是否打开监控、监控集群的fqdn、监听端口等）。Ansible在部署时将替换TDengine的配置文件中的这些参数。有关TDengine配置参数的更多信息，请参考[TDengine配置文档](https://docs.taosdata.com/reference/config)。

## 使用方法

1. 启动虚拟机：
   ```
   vagrant up
   ```

2. 创建集群：
   ```
   ansible-playbook deploy_master.yaml
   ```

3. 将远程节点加入集群：
   ```
   ansible-playbook add_nodes.yaml
   ```

4. 采集本机性能并写入TDengine：
   - 创建数据表： 
     ```
     python3 scripts/collect_performance/create_table.py
     ```
   - 采集数据每隔3秒写入

     *第一个参数为uid用于区分不同设备，例如采集uid为1的数据*
     ```
     python3 scripts/collect_performance/collecting.py 1
     ```

5. Grafana配置：
   - 在浏览器中打开：http://master_ip:3000，grafana初始用户为admin，密码为admin。
   - 在左侧功能列表中选择 `Data sources`，然后选择 `tdengine-datasource`。
   - 在 `TDengine Host` 中填写 http://127.0.0.1:6041，在 `TDengine Authentication` 中输入用户名: root，密码: taosdata。
   - 点击 `Save & Test`，如果弹出 `TDengine Data source is working`，则表示TDengine数据源导入成功。

6. 导入dashboard：
   - 在左侧功能列表中选择 Dashboards。
   - 在右上角选择 `New`，然后选择 `Import`。
   - 上传 `grafana-dashboard.json` 文件，选择TDengine数据源，完成导入。
