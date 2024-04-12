
import sys
import time
from tb_device_http import TBHTTPDevice
from PIL import Image,ImageGrab

try:
    # 响应RPC
    client = TBHTTPDevice('http://192.168.1.200:8080', sys.argv[1])
except Exception as e:
    logging.error(f"Failed to initialize device connection: {e}")
    sys.exit(1)

def callback(data):
    rpc_id = data['id']
    print(data)
    img = ImageGrab.grab()
    img = img.convert('RGB')
    print('pixel length:    '+ str(len(img.getdata())))
    # 将图片数据转换为Base64编码
    #base64_image = base64.b64encode(img.tobytes()).decode('utf-8')
    response_params = {'result': list(img.getdata())}
    print('begin response')
    client.send_rpc(name='rpc_response', rpc_id=rpc_id, params=response_params)
    print('rpc over')

client._TBHTTPDevice__config.update({'timeout': 10})
try:
    client.subscribe('rpc', callback)
except Exception as e:
    logging.error(f"Failed to subscribe rpc: {e}")

isRunning = True
while (isRunning):
    time.sleep(3)


