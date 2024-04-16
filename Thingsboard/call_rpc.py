import base64

import requests,json
import configparser
import stdiomask
from minio import Minio
from minio.error import S3Error

thingsboard_host:str
thingsboard_token:str
minio_client:Minio
def download_from_minio(bucket_name:str, file_name: str):
    try:
        image = minio_client.get_object(bucket_name, file_name)
        image_data = base64.b64encode(image.read()).decode('utf-8')
        with open(file_name, "wb") as file:
            file.write(base64.b64decode(image_data))
    except S3Error as e:
        print(f"An S3Error occurred: {e}  {file_name}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
def get_metadata():
    attr_url = f'http://{thingsboard_host}/api/v1/{thingsboard_token}/attributes?sharedKeys=device_id,minio_host,minio_access,minio_secret'
    response = requests.get(attr_url)
    shared_attrs = response.json().get('shared')
    if shared_attrs == None:
        raise ValueError("shared attribute does not exist")
    device_id = shared_attrs.get('device_id')
    if device_id == None:
        raise ValueError("device_id does not exist")
    minio_host = shared_attrs.get('minio_host')
    if minio_host == None:
        raise ValueError("minio_host does not exist")
    minio_access = shared_attrs.get('minio_access')
    if minio_access == None:
        raise ValueError("minio_access does not exist")
    minio_secret = shared_attrs.get('minio_secret')
    if minio_secret == None:
        raise ValueError("minio_secret does not exist")
    return device_id, minio_host, minio_access, minio_secret

def main():
    global thingsboard_host
    global thingsboard_token
    global minio_client
    jwt_token: str
    image_url: str
    config = configparser.ConfigParser()
    config.read('call_rpc.conf')
    thingsboard_host = config.get('thingsboard', 'host')
    thingsboard_token = config.get('thingsboard', 'device_token')

    username = input("Please enter your username: ")
    password = stdiomask.getpass(prompt='Password: ', mask='*')

    login_url = f'http://{thingsboard_host}/api/auth/login'
    credentials = {
        'username': username,
        'password': password
    }
    response = requests.post(login_url, data=json.dumps(credentials), headers={'Content-Type': 'application/json'})
    if response.status_code == 200:
        # 提取JWT Token
        jwt_token = response.json().get('token')
    elif response.status_code == 401:
        raise ValueError("username and password was wrong")
    print("jwt token success")

    device_id, minio_host, minio_access, minio_secret = get_metadata()
    minio_client = Minio(minio_host,
                         access_key=minio_access,
                         secret_key=minio_secret,
                         secure=False)

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
        params = response.json().get('params')
        print(f'response {params}')
        if params.get("upload_result") == "success" and "filename" in params and "bucket" in params:
            filename = params.get("filename")
            bucket_name = params.get("bucket")
            download_from_minio(bucket_name, filename)
    else:
        raise ValueError(f"request failed {response}")

if __name__ == "__main__":
    main()