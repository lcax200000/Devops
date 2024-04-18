
import requests,json
import stdiomask
import configparser
from injector import Module, multiprovider, provider,Injector, inject, singleton
from minio import Minio
from minio.error import S3Error

#####################################################################################
#                              Configuration                                        #
#####################################################################################
class Configuration:
    def __init__(self):
        config = configparser.ConfigParser()
        config.read('call_rpc.conf')
        self.host = config.get('thingsboard', 'host')
        self.token = config.get('thingsboard', 'device_token')

#####################################################################################
#                              Action                                               #
#####################################################################################
class InitModule(Module):
    @singleton
    @multiprovider
    def provide_information(self, configuration: Configuration) -> dict:
        return {'host': configuration.host, 'token': configuration.token}

class CallHandler:
    def download_from_minio(self, bucket_name: str, file_name: str):
        try:
            image = self.minio_client.get_object(bucket_name, file_name)
            with open(file_name, "wb") as file:
                file.write(image.read())
        except S3Error as e:
            print(f"An S3Error occurred: {e}  {file_name}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    def get_metadata(self):
        attr_url = f'http://{self.thingsboard_host}/api/v1/{self.thingsboard_token}/attributes?sharedKeys=device_id,minio_host,minio_access,minio_secret'
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
    def do_action(self):
        username = input("Please enter your username: ")
        password = stdiomask.getpass(prompt='Password: ', mask='*')

        login_url = f'http://{self.thingsboard_host}/api/auth/login'
        credentials = {
            'username': username.strip(),
            'password': password.strip()
        }
        response = requests.post(login_url, data=json.dumps(credentials), headers={'Content-Type': 'application/json'})
        if response.status_code == 200:
            # 提取JWT Token
            jwt_token = response.json().get('token')
        elif response.status_code == 401:
            raise ValueError("username and password was wrong")
        print("jwt token success")

        headers = {
            'Content-Type': 'application/json',
            'X-Authorization': f'Bearer {jwt_token}'
        }
        # 调用设备的RPC
        rpc_payload = {
            'method': 'TakePicture',
            'params': ''
        }
        response = requests.post(f"http://{self.thingsboard_host}/api/plugins/rpc/twoway/{self.device_id}", headers=headers,
                                 json=rpc_payload)
        if response.status_code == 200:
            params = response.json().get('params')
            print(f'response {params}')
            if params.get("upload_result") == "success" and "filename" in params and "bucket" in params:
                filename = params.get("filename")
                bucket_name = params.get("bucket")
                self.download_from_minio(bucket_name, filename)
        else:
            raise ValueError(f"request failed {response}")
    @inject
    def __init__(self, conf: dict):
        self.thingsboard_host = conf['host']
        self.thingsboard_token = conf['token']
        self.device_id, minio_host, minio_access, minio_secret = self.get_metadata()
        self.minio_client = Minio(minio_host,
                         access_key=minio_access,
                         secret_key=minio_secret,
                         secure=False)

#####################################################################################
#                              Main                                                 #
#####################################################################################
def configure_for_bind(binder):
    configuration = Configuration()
    binder.bind(Configuration, to=configuration, scope=singleton)

def main():
    injector = Injector([configure_for_bind, InitModule()])
    handler = injector.get(CallHandler)
    handler.do_action()

if __name__ == "__main__":
    main()
