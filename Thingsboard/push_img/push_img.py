import os
import time
import configparser
import base64
import hashlib
import schedule
from datetime import datetime
from io import BytesIO
from tb_device_http import TBHTTPDevice
from PIL import ImageGrab, Image
from minio import Minio
from minio.error import S3Error
from abc import ABC, abstractmethod
from enum import Enum

PhotographMode = Enum('PhotographMode', ('OnceCapture', 'IntervalCapture'))
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

class Photograph(ABC):
    @abstractmethod
    def take_photo(self):
        pass

class Agent:
    def __init__(self, worker: PlatformInterface):
        self.worker = worker
        self.isRunning = True
    def start_service(self):
        self.worker.fetch_and_handle_rpc()
        while self.isRunning:
            schedule.run_pending()
            time.sleep(1)
    def stop_service(self):
        self.worker.stop()
        self.isRunning = False

#####################################################################################
#                                Thingsboard                                        #
#####################################################################################
class ThingsboardRPC(PlatformInterface):
    def __init__(self, host: str, token: str, photograph: Photograph):
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
        self.photograph = photograph
        self.photograph_mode = PhotographMode.OnceCapture

    def create_bucket(self, bucket_name: str):
        try:
            if self.minio_client is not None and not self.minio_client.bucket_exists(bucket_name):
                self.minio_client.make_bucket(bucket_name)
        except S3Error as e:
            print(f"{datetime.now()} An S3Error occurred: {e}  {bucket_name}")
        except Exception as e:
            print(f"{datetime.now()} An unexpected error occurred: {e}")

    def upload_to_minio(self, bucket_name: str, local_file_path: str, object_name: str):
        try:
            if self.minio_client is not None:
                self.minio_client.fput_object(bucket_name, object_name, local_file_path)
        except S3Error as e:
            print(f"{datetime.now()} An S3Error occurred: {e}  {object_name}")
        except Exception as e:
            print(f"{datetime.now()} An unexpected error occurred: {e}")

    def download_from_minio(self, bucket_name: str, file_name: str):
        try:
            if self.minio_client is not None:
                image = self.minio_client.get_object(bucket_name, file_name)
                with open(file_name, "wb") as file:
                    file.write(image.read())
        except S3Error as e:
            print(f"{datetime.now()} An S3Error occurred: {e}  {file_name}")
        except Exception as e:
            print(f"{datetime.now()} An unexpected error occurred: {e}")

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
        if self.check_update(file_name, version) is False:
            self.thingsboard_client.send_rpc(name='rpc_response', rpc_id=rpc_id, params={'result': 'success'})
            self.thingsboard_client.send_telemetry({'message': 'package duplicate installation'}, queued=False)
            return
        self.thingsboard_client.send_telemetry({'state': 'DOWNLOADING', 'time': time.time()*1000}, queued=False)
        self.download_from_minio(bucket, file_name)
        if not os.path.exists(file_name):
            self.thingsboard_client.send_rpc(name='rpc_response', rpc_id=rpc_id, params={'result': 'failed'})
            self.thingsboard_client.send_telemetry({'message': 'download failed'}, queued=False)
            return
        self.thingsboard_client.send_rpc(name='rpc_response', rpc_id=rpc_id, params={'result': 'success'})
        time.sleep(1)
        self.thingsboard_client.send_telemetry({'state': 'DOWNLOADED'}, queued=False)
        time.sleep(1)
        self.download_from_minio(bucket, file_name + '.md5')
        if os.path.exists(file_name + '.md5'):
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

    def take_picture(self, get_image: bool, bucket: str = ''):
        img = self.photograph.take_photo()
        img.save('screenshot.jpg')
        now = datetime.now()
        formatted_time = now.strftime("%Y%m%d%H%M%S")
        filename = f"{formatted_time}_{self.device_id}.jpg"
        self.upload_to_minio(bucket if bucket else self.device_id, 'screenshot.jpg', filename)
        if get_image:
            buffered = BytesIO()
            img.save(buffered, format="JPEG")
            base64_data = base64.b64encode(buffered.getvalue()).decode('utf-8')
            self.thingsboard_client.send_telemetry({'Image': base64_data})
        return filename

    def callback(self, data):
        rpc_id = data['id']
        method = data['method']
        if method == 'TakePicture':
            if self.photograph_mode is not PhotographMode.OnceCapture:
                self.photograph_mode = PhotographMode.OnceCapture
                schedule.clear()
            get_image = False
            if "getImage" in data['params']:
                get_image = data['params'].get("getImage")
            filename = self.take_picture(get_image)
            response_params = {'filename': filename, 'bucket': self.device_id}
            self.thingsboard_client.send_rpc(name='rpc_response', rpc_id=rpc_id, params=response_params)
        elif method == 'Upgrade':
            bucket = data['params'].get("bucket")
            file_name = data['params'].get("filename")
            version = data['params'].get("version")
            self.upgrade(rpc_id, bucket, file_name, version)
        elif method == 'IntervalTakePicture':
                interval = data['params'].get("interval")
            bucket = data['params'].get("bucket")
            if self.photograph_mode is not PhotographMode.IntervalCapture:
                self.photograph_mode = PhotographMode.IntervalCapture
            else:
                schedule.clear()
            schedule.every(interval).seconds.do(self.take_picture, get_image=True, bucket=bucket)
        else:
            print(f"{datetime.now()} undefined method {method}")
        print(f'{datetime.now()} {method} rpc over')

    def get_metadata(self):
        client_keys = [TITLE_ATTR, VERSION_ATTR]
        shared_keys = ['device_id', 'minio_host', 'minio_access', 'minio_secret', TITLE_ATTR, VERSION_ATTR]
        data = self.thingsboard_client.request_attributes(client_keys=client_keys, shared_keys=shared_keys)
        shared_attrs = data.get('shared')
        if shared_attrs is None:
            raise ValueError("shared attribute does not exist")
        device_id = shared_attrs.get('device_id')
        if device_id is None:
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
        if current_title is None:
            current_title = ''
        current_version = client_attrs.get(VERSION_ATTR)
        if current_version is None:
            current_version = 0.1
        return device_id, minio_host, minio_access, minio_secret, current_title, current_version

    def fetch_and_handle_rpc(self):
        self.create_bucket(self.device_id)
        self.thingsboard_client.connect()
        self.thingsboard_client.subscribe('rpc', self.callback)

    def stop(self):
        self.thingsboard_client.stop_publish_worker()
        self.thingsboard_client.unsubscribe('rpc')

class Snapshot(Photograph):
    def take_photo(self) -> Image:
        return ImageGrab.grab()
#####################################################################################
#                                Main                                               #
#####################################################################################

def main():
    config = configparser.ConfigParser()
    config.read('push_img.conf')
    thingsboard = ThingsboardRPC(config.get('thingsboard', 'host'), config.get('thingsboard', 'device_token'), Snapshot())
    agent = Agent(thingsboard)
    try:
        agent.start_service()
    except KeyboardInterrupt:
        agent.stop_service()

if __name__ == "__main__":
    main()
