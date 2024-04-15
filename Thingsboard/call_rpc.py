import requests,json
import configparser
import stdiomask

def main():
    config = configparser.ConfigParser()
    config.read('call_rpc.conf')
    thingsboard_host = config.get('thingsboard', 'host')
    thingsboard_token = config.get('thingsboard', 'device_token')

    attr_url = f'http://{thingsboard_host}/api/v1/{thingsboard_token}/attributes?sharedKeys=device_id'
    response = requests.get(attr_url)

    shared_attrs = response.json().get('shared')
    if shared_attrs == None:
        raise ValueError("shared attribute does not exist")
    device_id = shared_attrs.get('device_id')
    if device_id == None:
        raise ValueError("device_id does not exist")

    login_url = f'http://{thingsboard_host}/api/auth/login'
    user_input = input("Please enter your username: ")
    password = stdiomask.getpass(prompt='Password: ', mask='*')

    # 用户的登录凭证
    credentials = {
        'username': user_input,
        'password': password
    }
    # 发送登录请求
    response = requests.post(login_url, data=json.dumps(credentials), headers={'Content-Type': 'application/json'})
    jwt_token = ""
    # 检查响应
    if response.status_code == 200:
        # 提取JWT Token
        jwt_token = response.json().get('token')
    else:
        print('Failed to login. Status code:', response.status_code)

    headers = {
        'Content-Type': 'application/json',
        'X-Authorization': f'Bearer {jwt_token}'
    }
    # 调用设备的RPC
    rpc_payload = {
        'method': 'TakePicture',
        'params': ''
    }

    response = requests.post(f"http://{thingsboard_host}/api/plugins/rpc/oneway/{device_id}", headers=headers, json=rpc_payload)
    print(response)

if __name__ == "__main__":
    main()