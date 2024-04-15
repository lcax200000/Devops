import requests,json
import configparser
import stdiomask

def main():
    jwt_token: str
    config = configparser.ConfigParser()
    config.read('call_rpc.conf')
    thingsboard_host = config.get('thingsboard', 'host')
    thingsboard_token = config.get('thingsboard', 'device_token')

    username = input("Please enter your username: ")
    password = stdiomask.getpass(prompt='Password: ', mask='*')

    attr_url = f'http://{thingsboard_host}/api/v1/{thingsboard_token}/attributes?sharedKeys=device_id'
    response = requests.get(attr_url)
    shared_attrs = response.json().get('shared')
    if shared_attrs == None:
        raise ValueError("shared attribute does not exist")
    device_id = shared_attrs.get('device_id')
    if device_id == None:
        raise ValueError("device_id does not exist")

    login_url = f'http://{thingsboard_host}/api/auth/login'
    credentials = {
        'username': username,
        'password': password
    }
    # 发送登录请求
    response = requests.post(login_url, data=json.dumps(credentials), headers={'Content-Type': 'application/json'})
    # 检查响应
    if response.status_code == 200:
        # 提取JWT Token
        jwt_token = response.json().get('token')
    elif response.status_code == 401:
        raise ValueError("username and password was wrong")

    headers = {
        'Content-Type': 'application/json',
        'X-Authorization': f'Bearer {jwt_token}'
    }
    # 调用设备的RPC
    rpc_payload = {
        'method': 'TakePicture',
        'params': ''
    }

    response = requests.post(f"http://{thingsboard_host}/api/plugins/rpc/twoway/{device_id}", headers=headers,
                             json=rpc_payload)
    if response.status_code == 200:
        print(response.json().get('params'))
    else:
        raise ValueError("please try again")

if __name__ == "__main__":
    main()