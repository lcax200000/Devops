

*本项目通过使用docker compose创建单节点Thingsboard平台。
push_img.py用于响应平台请求，获取截图并上传至Minio S3*


## 使用方法

1. 启动虚拟机：
   ```
   运行 deploy_single.sh
   ```

2. 登入Thingsboard平台，默认用户名: tenant@thingsboard.org，密码: tenant

3. 创建设备，为设备创建access token.

4. 导入规则链文件: root_rule_chain.json.

4. 配置push_img.conf.

  - `[thingsboard]`下填写Thingsboard平台host和设备生成的access token
  - `[minio]`下填写Minio平台host、access token和secret token
   
5. 设备端运行脚本 push_img.py.

6. Thingsboard平台的Dashboard中添加`Service RPC`部件，选择刚才创建的设备，发起rpc请求。

7. 在配置的S3存储中查看截图。