
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
bucket_name:str

def upload_to_minio(local_file_path: str, object_name: str):
    try:
        minio_client.fput_object(bucket_name, object_name, local_file_path)
        return True
    except S3Error as err:
        print(err)
        return False


def take_picture(rpc_id:int):
    img = ImageGrab.grab()
    img.save('screenshot.jpg')
    now = datetime.now()
    formatted_time = now.strftime("%Y%m%d%H%M%S")
    filename = f"{formatted_time}_{device_id}.jpg"
    res = upload_to_minio('screenshot.jpg', filename)
    if res == True:
        response_params = {'result': f'{minio_host}/{bucket_name}/{filename}'}
    else:
        response_params = {'result': 'Failed'}
    thingsboard_client.send_rpc(name='rpc_response', rpc_id=rpc_id, params=response_params)

def callback(data):
    rpc_id = data['id']
    method = data['method']
    if method == 'TakePicture':
        take_picture(rpc_id)
    print('rpc over')

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
    bucket_name = shared_attrs.get('bucket_name')
    if bucket_name == None:
        raise ValueError("bucket_name does not exist")
    return device_id, minio_host, minio_access, minio_secret, bucket_name

def main():
    global thingsboard_client
    global minio_client
    global device_id
    global minio_host
    global bucket_name

    config = configparser.ConfigParser()
    config.read('push_img.conf')
    thingsboard_host = config.get('thingsboard', 'host')
    thingsboard_token = config.get('thingsboard', 'device_token')

    thingsboard_client = TBHTTPDevice(f'http://{thingsboard_host}', thingsboard_token)
    thingsboard_client._TBHTTPDevice__config.update({'timeout': 10})
    device_id, minio_host, minio_access, minio_secret, bucket_name = get_metadata()
    minio_client = Minio(minio_host,
                         access_key=minio_access,
                         secret_key=minio_secret,
                         secure=False)
    thingsboard_client.subscribe('rpc', callback)
    isRunning = True
    while (isRunning):
        time.sleep(3)

if __name__ == "__main__":
    main()
