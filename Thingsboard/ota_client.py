import configparser
import os
import time
import traceback
import requests
from zlib import crc32
from hashlib import sha256, sha384, sha512, md5
from mmh3 import hash, hash128
from math import ceil

OTA_PLATFORM = ['fw', 'sw']
CHECKSUM_ATTR = "_checksum"
CHECKSUM_ALG_ATTR = "_checksum_algorithm"
SIZE_ATTR = "_size"
TITLE_ATTR = "_title"
VERSION_ATTR = "_version"
STATE_ATTR = "_state"
CHUNK_SIZE = 'chunk_size'
class PlatformInterface:
    def get_ware_info(self, platform: int) -> dict:
        return {}
    def check_update(self, platform: int, ware_info: dict):
        return
    def upgrade(self, platform: int, ware_info: dict):
        return
    def release(self):
        return

class Agent:
    def __init__(self, worker: PlatformInterface):
        self.worker = worker
        self.isRunning = True
    def start_service(self):
        while (self.isRunning):
            try:
                for i in range(len(OTA_PLATFORM)):
                    firmware_info = self.worker.get_ware_info(i)
                    print("firmware_info ", firmware_info, i)
                    if self.worker.check_update(i, firmware_info):
                        self.worker.upgrade(i, firmware_info)
                    time.sleep(3)
            except requests.exceptions.RequestException as e:
                print("An error occurred:", e)
                traceback.print_stack()
            except Exception as e:
                print("Exception ", e)
                traceback.print_stack()

    def stop_service(self):
        self.isRunning = False
        self.worker.release()

class ThingsboardRPC(PlatformInterface):
    def __init__(self, host:str, token:str):
        self.current_ware_info = [{
            "current_fw_title": None,
            "current_fw_version": None
        }, {
            "current_sw_title": None,
            "current_sw_version": None
        }]
        self.host = host
        self.token = token
        self.package_name = ""

    def send_telemetry(self, telemetry):
        requests.post(f"http://{self.host}/api/v1/{self.token}/telemetry", json=telemetry)

    def get_ware_info(self, platform: int) -> dict:
        keys = [OTA_PLATFORM[platform]+CHECKSUM_ATTR, OTA_PLATFORM[platform]+CHECKSUM_ALG_ATTR, OTA_PLATFORM[platform] +
                SIZE_ATTR, OTA_PLATFORM[platform]+TITLE_ATTR, OTA_PLATFORM[platform]+VERSION_ATTR, CHUNK_SIZE]
        response = requests.get(f"http://{self.host}/api/v1/{self.token}/attributes", params={"sharedKeys": keys}).json()
        return response.get("shared", {})

    def check_update(self, platform: int, ware_info: dict):
        if (ware_info.get(OTA_PLATFORM[platform]+VERSION_ATTR) is not None and ware_info.get(OTA_PLATFORM[platform] + VERSION_ATTR) != self.current_ware_info[platform].get("current_" + OTA_PLATFORM[platform] + VERSION_ATTR)) \
                or (ware_info.get(OTA_PLATFORM[platform]+TITLE_ATTR) is not None and ware_info.get(OTA_PLATFORM[platform] + TITLE_ATTR) != self.current_ware_info[platform].get('current_' + OTA_PLATFORM[platform] + TITLE_ATTR)):
            return True
        return False

    def upgrade(self, platform: int, ware_info: dict):
        print("upgrade ", ware_info, platform)
        self.current_ware_info[platform][f'current_{OTA_PLATFORM[platform]}{TITLE_ATTR}'] = None
        self.current_ware_info[platform][f'current_{OTA_PLATFORM[platform]}{VERSION_ATTR}'] = None
        self.package_name = ware_info.get(OTA_PLATFORM[platform] + TITLE_ATTR)

        self.send_telemetry({OTA_PLATFORM[platform]+STATE_ATTR: "DOWNLOADING"})
        time.sleep(1)
        # If 'chunk_size' is not configured in the device attribute, the entire file will be downloaded at once by default.
        data = self.get_ware(platform, ware_info, ware_info.get(CHUNK_SIZE, 0))
        self.send_telemetry({OTA_PLATFORM[platform]+STATE_ATTR: "DOWNLOADED"})
        verification_result = self.verify_checksum(data, ware_info.get(OTA_PLATFORM[platform] + CHECKSUM_ALG_ATTR),
                                                   ware_info.get(OTA_PLATFORM[platform] + CHECKSUM_ATTR))
        if verification_result:
            print("Checksum verified!")
            self.send_telemetry({OTA_PLATFORM[platform] + STATE_ATTR: "VERIFIED"})
        else:
            # checksum failed, please try again later
            print("Checksum verification failed!")
            self.send_telemetry({OTA_PLATFORM[platform] + STATE_ATTR: "FAILED"})
            os.remove(self.package_name)
            return
        time.sleep(1)
        print("UPDATING   ")
        self.send_telemetry({OTA_PLATFORM[platform]+STATE_ATTR: "UPDATING"})
        time.sleep(1)
        self.current_ware_info[platform][f'current_{OTA_PLATFORM[platform]}{TITLE_ATTR}'] = ware_info.get(OTA_PLATFORM[platform] + TITLE_ATTR)
        self.current_ware_info[platform][f'current_{OTA_PLATFORM[platform]}{VERSION_ATTR}'] = ware_info.get(OTA_PLATFORM[platform] + VERSION_ATTR)
        result_dict = {
            OTA_PLATFORM[platform]+STATE_ATTR: "UPDATED"
        }
        result_dict.update(self.current_ware_info[platform])
        self.send_telemetry(result_dict)
        print('upgrade over ', platform)
        os.remove(self.package_name)

    def get_ware(self, platform: int, info: dict, chunk_size: int):
        with open(info.get(OTA_PLATFORM[platform]+TITLE_ATTR), 'w') as file:
            pass
        chunk_count = ceil(info.get(OTA_PLATFORM[platform]+SIZE_ATTR, 0) / chunk_size) if chunk_size > 0 else 0
        firmware_data = b''
        for chunk_number in range(chunk_count + 1):
            params = {"title": info.get(OTA_PLATFORM[platform]+TITLE_ATTR),
                      "version": info.get(OTA_PLATFORM[platform]+VERSION_ATTR),
                      "size": chunk_size if chunk_size < info.get(OTA_PLATFORM[platform]+SIZE_ATTR) else info.get(OTA_PLATFORM[platform]+SIZE_ATTR),
                        "chunk": chunk_number}
            print(f'Getting chunk with number: {chunk_number + 1}. Chunk size is : {chunk_size} byte(s).')
            if platform == 0:
                response = requests.get(
                    f"http://{self.host}/api/v1/{self.token}/firmware",
                    params=params)
            else:
                response = requests.get(
                    f"http://{self.host}/api/v1/{self.token}/software",
                    params=params)
            if response.status_code != 200:
                print("Received error:")
                response.raise_for_status()
                return
            with open(info.get(OTA_PLATFORM[platform]+TITLE_ATTR), "ab") as firmware_file:
                firmware_file.write(response.content)
            firmware_data += response.content
        return firmware_data

    def verify_checksum(self, firmware_data, checksum_alg, checksum):
        if firmware_data is None:
            print("Firmware wasn't received!")
            return False
        if checksum is None:
            print("Checksum was't provided!")
            return False
        checksum_of_received_firmware = None
        print(f"Checksum algorithm is: {checksum_alg}")
        if checksum_alg.lower() == "sha256":
            checksum_of_received_firmware = sha256(firmware_data).digest().hex()
        elif checksum_alg.lower() == "sha384":
            checksum_of_received_firmware = sha384(firmware_data).digest().hex()
        elif checksum_alg.lower() == "sha512":
            checksum_of_received_firmware = sha512(firmware_data).digest().hex()
        elif checksum_alg.lower() == "md5":
            checksum_of_received_firmware = md5(firmware_data).digest().hex()
        elif checksum_alg.lower() == "murmur3_32":
            reversed_checksum = f'{hash(firmware_data, signed=False):0>2X}'
            if len(reversed_checksum) % 2 != 0:
                reversed_checksum = '0' + reversed_checksum
            checksum_of_received_firmware = "".join(
                reversed([reversed_checksum[i:i + 2] for i in range(0, len(reversed_checksum), 2)])).lower()
        elif checksum_alg.lower() == "murmur3_128":
            reversed_checksum = f'{hash128(firmware_data, signed=False):0>2X}'
            if len(reversed_checksum) % 2 != 0:
                reversed_checksum = '0' + reversed_checksum
            checksum_of_received_firmware = "".join(
                reversed([reversed_checksum[i:i + 2] for i in range(0, len(reversed_checksum), 2)])).lower()
        elif checksum_alg.lower() == "crc32":
            reversed_checksum = f'{crc32(firmware_data) & 0xffffffff:0>2X}'
            if len(reversed_checksum) % 2 != 0:
                reversed_checksum = '0' + reversed_checksum
            checksum_of_received_firmware = "".join(
                reversed([reversed_checksum[i:i + 2] for i in range(0, len(reversed_checksum), 2)])).lower()
        else:
            print("Client error. Unsupported checksum algorithm.")
        print(checksum_of_received_firmware)
        return checksum_of_received_firmware == checksum
    def release(self):
        os.remove(self.package_name)
        return

def main():
    config = configparser.ConfigParser()
    config.read('ota_client.conf')
    config.get('thingsboard', 'host')
    config.get('thingsboard', 'device_token')
    thingsboard = ThingsboardRPC(config.get('thingsboard', 'host'), config.get('thingsboard', 'device_token'))
    agent = Agent(thingsboard)
    agent.start_service()

if __name__ == "__main__":
    main()
