本项目通过Vagrant管理虚拟机，使用Ansible创建TDengine的master节点并且添加node节点进入集群。

准备：
1.确保ansible控制节点和目标节点的ssh连通。
2.ansible控制节点本地的/etc/hosts和/etc/ansible/hosts中分别存在被控节点的host信息。
3.修改deploy_master.yaml第一行"host"值为被控节点的hostname。
4.根据需要配置TDengine模板文件resources/config/tempelete_conf，将需要变更的TDengine配置项添加到文件中(如是否打开监控，监控集群的fqdn，监听端口等)，Ansible会在部署的时候替换到TDengine的配置文件中，关于TDengine配置参数见:https://docs.taosdata.com/reference/config。

启动虚拟机：
vagrant up

创建集群：
ansible-playbook deploy_master.yaml

将远程节点加入集群:
ansible-playbook add_nodes.yaml

采集本机性能并写入TDengine：
1.创建数据表: 
 python3 scripts/collect_performance/create_table.py
2.采集数据每隔3秒写入，后面第一个参数为uid用于区分不同设备，如采集uid为1的数据:
 python3 scripts/collect_performance/collecting.py 1

grafana配置:
1.浏览器打开: http://master ip:3000, grafana初始用户:admin，密码:admin。
2.左侧功能列表选择 "Data sources"，选择"tdengine-datasource"。
3."TDengine Host"中填写http://127.0.0.1:6041，"TDengine Authentication"中输入用户名: root，密码: taosdata。
4.Save&test后，弹出"TDengine Data source is working"，TDengine datasource导入完成。

导入dashboard:
1.左侧功能列表选择 Dashboards。
2.右上角选择"New"，下拉菜单选择"Import"。
3.上传grafana-dashboard.json，tdengine-datasource数据源选择TDengine datasource，Import导入完成。