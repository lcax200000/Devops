from agent import AgentHandler
import time
import configparser
from injector import Module, provider, Injector, inject, singleton
from tb_device_http import TBHTTPDevice

class Configuration:
    def __init__(self):
        config = configparser.ConfigParser()
        config.read('push_img.conf')
        self.host = config.get('thingsboard', 'host')
        self.token = config.get('thingsboard', 'device_token')

class InitModule(Module):
    @singleton
    @provider
    def provide_connection(self, configuration: Configuration) -> TBHTTPDevice:
        thingsboard_client = TBHTTPDevice(f'http://{configuration.host}', configuration.token)
        thingsboard_client._TBHTTPDevice__config.update({'timeout': 10})
        return thingsboard_client

def configure_for_bind(binder):
    configuration = Configuration()
    binder.bind(Configuration, to=configuration, scope=singleton)

def main():
    injector = Injector([configure_for_bind, InitModule()])
    handler = injector.get(AgentHandler)
    handler.start_service()
    isRunning = True
    while (isRunning):
        time.sleep(3)

if __name__ == "__main__":
    main()
