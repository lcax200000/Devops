
import threading
import time
import psutil
import sys
#import taosws
from taosrest import connect, TaosRestConnection, TaosRestCursor
cancel_tmr = False
conn = {}
def start():
    # 获取CPU信息
    cpus = psutil.cpu_times(percpu=True)
    # 获取总体CPU使用率，如果想要每个CPU的使用率，可以使用psutil.cpu_percent(interval=None, percpu=True)
    cpu_usage = psutil.cpu_percent(interval=1)
    # 获取内存信息
    memory = psutil.virtual_memory()
    # 获取交换分区信息
    swap = psutil.swap_memory()
    # 获取磁盘I/O信息
    disks = psutil.disk_io_counters(perdisk=True)
    # 获取网络I/O信息
    net_io = psutil.net_io_counters()
    sqlCmd = "insert into server_performance" + sys.argv[1] + " using server_performance TAGS (%s) values (now,%f,%d,%d,%d)" % (sys.argv[1], cpu_usage, memory.available/1000, net_io.bytes_recv/1000, net_io.bytes_sent/1000)
    print(conn.execute(sqlCmd))



def heart_beat():
    # 打印当前时间
    print(time.strftime('%Y-%m-%d %H:%M:%S'))
    if not cancel_tmr:
        start()
        # 每隔3秒执行一次
        threading.Timer(3, heart_beat).start()


if __name__ == '__main__':
    # conn = taos.connect(host="192.168.1.200",
    #                     port=6030,
    #                     database="log")
    #conn = taosws.connect("taosws://root:taosdata@192.168.1.200:6041")
    conn = connect(url="http://192.168.56.31:6041",
               user="root",
               password="taosdata",
               timeout=30,
               database="log")
    heart_beat()
    while(True):
        time.sleep(3)
