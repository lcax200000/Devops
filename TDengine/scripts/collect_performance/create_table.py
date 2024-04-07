from taosrest import connect, TaosRestConnection, TaosRestCursor
import sys

def create():
    # all parameters are optional.
    # if database is specified,
    # then it must exist.
    conn = connect(url="http://192.168.56.31:6041",
               user="root",
               password="taosdata",
               timeout=30,
               database="log")
    print('conn info:', conn)

    conn.execute('CREATE STABLE IF NOT EXISTS server_performance (ts TIMESTAMP, cpu_usage float, memory_available int, '
                 'bytes_recv int, bytes_sent int) TAGS (uid int)')
    conn.close()


if __name__ == "__main__":
    create()
