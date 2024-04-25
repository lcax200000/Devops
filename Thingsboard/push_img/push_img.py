import os
import time
import configparser
import base64
import hashlib
from datetime import datetime
from io import BytesIO
from tb_device_http import TBHTTPDevice
from PIL import ImageGrab
from minio import Minio
from minio.error import S3Error

TITLE_ATTR = "push_img_title"
VERSION_ATTR = "push_img_version"

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
        self.device_id, minio_host, minio_access, minio_secret, current_title, current_version = self.get_metadata()
        if minio_host is not None and minio_access is not None and minio_secret is not None:
            self.minio_client = Minio(minio_host,
                                      access_key=minio_access,
                                      secret_key=minio_secret,
                                      secure=False)
        else:
            self.minio_client = None
        print(self.thingsboard_client)
        print(self.minio_client)
        self.current_ware_info = {
            TITLE_ATTR: current_title,
            VERSION_ATTR: current_version
        }
    def create_bucket(self, bucket_name: str):
        try:
            if self.minio_client is not None and not self.minio_client.bucket_exists(bucket_name):
                self.minio_client.make_bucket(bucket_name)
        except S3Error as e:
            print(f"An S3Error occurred: {e}  {bucket_name}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    def upload_to_minio(self, bucket_name: str, local_file_path: str, object_name: str):
        success = False
        try:
            if self.minio_client is not None:
                self.minio_client.fput_object(bucket_name, object_name, local_file_path)
                success = True
        except S3Error as e:
            print(f"An S3Error occurred: {e}  {object_name}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
        return success

    def download_from_minio(self, bucket_name: str, file_name: str):
        success = False
        try:
            if self.minio_client is not None:
                image = self.minio_client.get_object(bucket_name, file_name)
                with open(file_name, "wb") as file:
                    file.write(image.read())
                success = True
        except S3Error as e:
            success = False
            print(f"An S3Error occurred: {e}  {file_name}")
        except Exception as e:
            success = False
            print(f"An unexpected error occurred: {e}")
        return success

    def calculate_md5(self, file_path):
        md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5.update(chunk)
        return md5.hexdigest()

    def verify_md5(self, file_path, expected_md5):
        calculated_md5 = self.calculate_md5(file_path)
        if calculated_md5 == expected_md5:
            return True
        else:
            return False

    def check_update(self, title: str, version: float):
        if (self.current_ware_info.get(TITLE_ATTR) != title or
                self.current_ware_info.get(VERSION_ATTR) != version):
            return True
        return False

    def upgrade(self, rpc_id: int, bucket: str, file_name: str, version: float):
        self.thingsboard_client.send_telemetry({'target_title': file_name, 'target_version': version, 'message': ''}, queued=False)
        if self.check_update(file_name, version) == False:
            self.thingsboard_client.send_rpc(name='rpc_response', rpc_id=rpc_id, params={'result': 'success'})
            self.thingsboard_client.send_telemetry({'message': 'package duplicate installation'}, queued=False)
            return
        self.thingsboard_client.send_telemetry({'state': 'DOWNLOADING', 'time': time.time()*1000}, queued=False)
        res = self.download_from_minio(bucket, file_name)
        md5_res = self.download_from_minio(bucket, file_name + '.md5')
        if res == False:
            self.thingsboard_client.send_rpc(name='rpc_response', rpc_id=rpc_id, params={'result': 'failed'})
            self.thingsboard_client.send_telemetry({'message': 'download failed'}, queued=False)
            return
        self.thingsboard_client.send_rpc(name='rpc_response', rpc_id=rpc_id, params={'result': 'success'})
        time.sleep(1)
        self.thingsboard_client.send_telemetry({'state': 'DOWNLOADED'}, queued=False)
        time.sleep(1)
        if md5_res:
            with open(file_name + '.md5', "r") as f:
                expected_md5 = f.read().strip()
            if not self.verify_md5(file_name, expected_md5):
                self.thingsboard_client.send_rpc(name='rpc_response', rpc_id=rpc_id, params={'result': 'failed'})
                self.thingsboard_client.send_telemetry({'state': 'VERIFIE FAILED', 'message': 'MD5 verification failed'}, queued=False)
                return
            else:
                self.thingsboard_client.send_telemetry({'state': 'VERIFIED'}, queued=False)
        time.sleep(1)
        self.thingsboard_client.send_telemetry({'state': 'UPDATING'}, queued=False)
        time.sleep(1)
        self.thingsboard_client.send_telemetry({'current_title': file_name, 'current_version': version,
                                                'state': 'UPDATED', 'message': 'upgrade success'}, queued=False)
        self.current_ware_info[TITLE_ATTR] = file_name
        self.current_ware_info[VERSION_ATTR] = version
        self.thingsboard_client.send_attributes(self.current_ware_info)
        self.stop()
        os._exit(0)

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
        self.thingsboard_client.send_rpc(name='rpc_response', rpc_id=rpc_id, params=response_params)
        if get_image == True:
            buffered = BytesIO()
            img.save(buffered, format="JPEG")
            base64_data = base64.b64encode(buffered.getvalue()).decode('utf-8')
            self.thingsboard_client.send_attributes({'Image': base64_data})

    def callback(self, data):
        rpc_id = data['id']
        method = data['method']
        if method == 'TakePicture':
            get_image = False
            if "getImage" in data['params']:
                get_image = data['params'].get("getImage")
            self.take_picture(rpc_id, get_image)
        elif method == 'Upgrade':
            bucket = data['params'].get("bucket")
            file_name = data['params'].get("filename")
            version = data['params'].get("version")
            self.upgrade(rpc_id, bucket, file_name, version)
        else:
            print(f"undefined method {method}")
        print(f'{method} rpc over')

    def get_metadata(self):
        client_keys = [TITLE_ATTR, VERSION_ATTR]
        shared_keys = ['device_id', 'minio_host', 'minio_access', 'minio_secret', TITLE_ATTR, VERSION_ATTR]
        data = self.thingsboard_client.request_attributes(client_keys=client_keys, shared_keys=shared_keys)
        shared_attrs = data.get('shared')
        if shared_attrs == None:
            raise ValueError("shared attribute does not exist")
        device_id = shared_attrs.get('device_id')
        if device_id == None:
            raise ValueError("device_id does not exist")
        minio_host = shared_attrs.get('minio_host')
        # if minio_host == None:
        #     raise ValueError("minio_host does not exist")
        minio_access = shared_attrs.get('minio_access')
        # if minio_access == None:
        #     raise ValueError("minio_access does not exist")
        minio_secret = shared_attrs.get('minio_secret')
        # if minio_secret == None:
        #     raise ValueError("minio_secret does not exist")

        client_attrs = data.get('client')
        current_title = client_attrs.get(TITLE_ATTR)
        if current_title == None:
            current_title = ''
        current_version = client_attrs.get(VERSION_ATTR)
        if current_version == None:
            current_version = 'v0.1'
        return device_id, minio_host, minio_access, minio_secret, current_title, current_version

    def fetch_and_handle_rpc(self):
        self.create_bucket(self.device_id)
        self.thingsboard_client.connect()
        self.thingsboard_client.subscribe('rpc', self.callback)

    def stop(self):
        self.thingsboard_client.stop_publish_worker()
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
