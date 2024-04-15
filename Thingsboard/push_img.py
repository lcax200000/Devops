from datetime import datetime

import requests
import time
from PIL import Image,ImageGrab
from minio import Minio
from minio.error import S3Error
import configparser

minio_client:Minio
isRunnging = True
DeviceName = ""
def upload_to_minio(bucket_name:str, local_file_path:str, object_name:str):
    try:
        print(minio_client.fput_object(bucket_name, object_name, local_file_path))
    except S3Error as err:
        print(err)

def fetch_and_handle_rpc(host:str, token:str, timeput:int):
    # ThingsBoard的RPC请求API
    rpc_url = f"{host}/api/v1/{token}/rpc"
    session = requests.session()
    session.headers.update({'Content-Type': 'application/json'})
    params = {
        'timeout': timeput * 1000
    }
    while True:
        try:
            # 发起GET请求以检查是否有RPC请求
            response = session.get(rpc_url, params=params, timeout=timeput * 1000)
            response.raise_for_status()

            if response.status_code == 200:
                rpc_request = response.json()
                print(f"Received RPC request: {rpc_request}")
                img = ImageGrab.grab()
                img.save('screenshot.jpg')
                now = datetime.now()
                formatted_time = now.strftime("%Y%m%d%H%M%S")
                upload_to_minio("thingsboard", 'screenshot.jpg', f"{formatted_time}_{DeviceName}.png")
                response_data = {'result': 'success'}
                rpc_response_url = f"{host}/api/v1/{token}/rpc/{rpc_request['id']}"
                print('resp: ', session.post(rpc_response_url, json=response_data))
                print('over')
        except requests.exceptions.Timeout:
            pass
        except requests.exceptions.HTTPError as err:
            if response.status_code == 408:  # Request timeout
                continue
            if response.status_code == 504:  # Gateway Timeout
                continue
            print(f"HTTP error: {err}")
        except requests.exceptions.RequestException as err:
            print(f"Error: {err}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

def request_rpc(host:str, token:str, method:str,params:{}):
    rpc_url = f"{host}/api/v1/{token}/rpc"
    headers = {
        'Content-Type': 'application/json',
    }
    payload = {
        'method': method,
        'params': params
    }
    response = requests.post(rpc_url, headers=headers, json=payload)
    print(f"request_rpc {method} response ", response.json())
    if response.status_code == 200:
        print(f'{method} RPC success')
    else:
        print('RPC failed! ', response)
    response.close()
    return response.json()

def main():
    global minio_client
    global DeviceName
    config = configparser.ConfigParser()

    config.read('push_img.conf')
    thingsboard_host = config.get('thingsboard', 'host')
    thingsboard_token = config.get('thingsboard', 'device_token')
    minio_client = Minio(config.get('minio', 'host'),
                         access_key=config.get('minio', 'access'),
                         secret_key=config.get('minio', 'secret'),
                         secure=False)

    meta = request_rpc(thingsboard_host, thingsboard_token, 'GetMetadata', {})
    if 'deviceName' not in meta:
        raise KeyError("'deviceName' not found in platform")
    DeviceName = str(meta["deviceName"]).strip().replace(" ", "_")
    while isRunnging:
        fetch_and_handle_rpc(thingsboard_host, thingsboard_token, 30)
        time.sleep(3)


if __name__ == "__main__":
    main()
