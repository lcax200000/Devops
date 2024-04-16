import base64
import sys
import time
import configparser
from datetime import datetime
from tb_device_http import TBHTTPDevice
from PIL import Image,ImageGrab
from minio import Minio
from minio.error import S3Error

thingsboard_client:TBHTTPDevice
minio_client:Minio
minio_host:str
device_id:str

def create_bucket(bucket_name:str):
    try:
        if not minio_client.bucket_exists(bucket_name):
            minio_client.make_bucket(bucket_name)
    except S3Error as e:
        print(f"An S3Error occurred: {e}  {bucket_name}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


def upload_to_minio(bucket_name:str, local_file_path: str, object_name: str):
    try:
        minio_client.fput_object(bucket_name, object_name, local_file_path)
        return True
    except S3Error as e:
        print(f"An S3Error occurred: {e}  {object}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    return False

def take_picture(rpc_id:int, get_image:bool):
    img = ImageGrab.grab()
    img.save('screenshot.jpg')
    now = datetime.now()
    formatted_time = now.strftime("%Y%m%d%H%M%S")
    filename = f"{formatted_time}_{device_id}.jpg"
    res = upload_to_minio(device_id, 'screenshot.jpg', filename)
    response_params = {}
    if res == True:
        response_params['url'] = filename
        response_params['bucket'] = device_id
    else:
        response_params['result'] = 'Failed'
    if get_image == True:
        response_params['image'] = base64.b64encode(img.tobytes()).decode('utf-8')
    thingsboard_client.send_rpc(name='rpc_response', rpc_id=rpc_id, params=response_params)

def callback(data):
    rpc_id = data['id']
    method = data['method']
    getImage = False
    if "getImage" in data['params']:
        getImage = data['params'].get("getImage")
    if method == 'TakePicture':
        take_picture(rpc_id, getImage)
    else:
        print(f"undefined method {method}")
    print(f'{method} rpc over')

def get_metadata():
    shared_keys = ['device_id', 'minio_host', 'minio_access', 'minio_secret']
    data = thingsboard_client.request_attributes(shared_keys=shared_keys)
    shared_attrs = data.get('shared')
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
    global thingsboard_client
    global minio_client
    global device_id
    global minio_host

    config = configparser.ConfigParser()
    config.read('push_img.conf')
    thingsboard_host = config.get('thingsboard', 'host')
    thingsboard_token = config.get('thingsboard', 'device_token')

    thingsboard_client = TBHTTPDevice(f'http://{thingsboard_host}', thingsboard_token)
    thingsboard_client._TBHTTPDevice__config.update({'timeout': 10})
    device_id, minio_host, minio_access, minio_secret = get_metadata()
    minio_client = Minio(minio_host,
                         access_key=minio_access,
                         secret_key=minio_secret,
                         secure=False)
    create_bucket(device_id)
    thingsboard_client.subscribe('rpc', callback)
    isRunning = True
    while (isRunning):
        time.sleep(3)

if __name__ == "__main__":
    main()
