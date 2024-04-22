import time
import configparser
import base64
from datetime import datetime
from tb_device_http import TBHTTPDevice
from PIL import ImageGrab
from minio import Minio
from minio.error import S3Error

#####################################################################################
#                                Agent                                              #
#####################################################################################
class PlatformInterface:
    def fetch_and_handle_rpc(self):
        return
    def stop(self):
        return

class Agent:
    def __init__(self, worker: PlatformInterface):
        self.worker = worker
        self.isRunning = True
    def start_service(self):
        self.worker.fetch_and_handle_rpc()
        while self.isRunning:
            time.sleep(3)
    def stop_service(self):
        self.worker.stop()
        self.isRunning = False

#####################################################################################
#                                Thingsboard                                        #
#####################################################################################
class ThingsboardRPC(PlatformInterface):
    def __init__(self, host: str, token: str):
        self.thingsboard_client = TBHTTPDevice(f'http://{host}', token)
        self.thingsboard_client._TBHTTPDevice__config.update({'timeout': 10})
        self.device_id, minio_host, minio_access, minio_secret = self.get_metadata()
        self.minio_client = Minio(minio_host,
                                  access_key=minio_access,
                                  secret_key=minio_secret,
                                  secure=False)
        print(self.thingsboard_client)
        print(self.minio_client)
    def create_bucket(self, bucket_name: str):
        try:
            if not self.minio_client.bucket_exists(bucket_name):
                self.minio_client.make_bucket(bucket_name)
        except S3Error as e:
            print(f"An S3Error occurred: {e}  {bucket_name}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    def upload_to_minio(self, bucket_name: str, local_file_path: str, object_name: str):
        success = False
        try:
            self.minio_client.fput_object(bucket_name, object_name, local_file_path)
            success = True
        except S3Error as e:
            print(f"An S3Error occurred: {e}  {object_name}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
        return success

    def take_picture(self, rpc_id: int, get_image: bool):
        img = ImageGrab.grab()
        img.save('screenshot.jpg')
        now = datetime.now()
        formatted_time = now.strftime("%Y%m%d%H%M%S")
        filename = f"{formatted_time}_{self.device_id}.jpg"
        res = self.upload_to_minio(self.device_id, 'screenshot.jpg', filename)
        response_params = {}
        if res == True:
            response_params['filename'] = filename
            response_params['bucket'] = self.device_id
            response_params['upload_result'] = 'success'
        else:
            response_params['upload_result'] = 'failed'
        if get_image == True:
            response_params['image'] = base64.b64encode(img.tobytes()).decode('utf-8')
        self.thingsboard_client.send_rpc(name='rpc_response', rpc_id=rpc_id, params=response_params)

    def callback(self, data):
        rpc_id = data['id']
        method = data['method']
        get_image = False
        if "getImage" in data['params']:
            get_image = data['params'].get("getImage")
        if method == 'TakePicture':
            self.take_picture(rpc_id, get_image)
        else:
            print(f"undefined method {method}")
        print(f'{method} rpc over')

    def get_metadata(self):
        shared_keys = ['device_id', 'minio_host', 'minio_access', 'minio_secret']
        data = self.thingsboard_client.request_attributes(shared_keys=shared_keys)
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

    def fetch_and_handle_rpc(self):
        self.create_bucket(self.device_id)
        self.thingsboard_client.subscribe('rpc', self.callback)
    def stop(self):
        self.thingsboard_client.unsubscribe('rpc')

#####################################################################################
#                                Main                                               #
#####################################################################################

def main():
    config = configparser.ConfigParser()
    config.read('push_img.conf')
    thingsboard = ThingsboardRPC(config.get('thingsboard', 'host'), config.get('thingsboard', 'device_token'))
    agent = Agent(thingsboard)
    try:
        agent.start_service()
    except KeyboardInterrupt:
        agent.stop_service()

if __name__ == "__main__":
    main()
