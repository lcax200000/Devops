from taosrest import connect, TaosRestConnection, TaosRestCursor


def create():
    # all parameters are optional.
    # if database is specified,
    # then it must exist.
    conn = connect(url="http://192.168.1.200:6041",
               user="root",
               password="taosdata",
               timeout=30,
               database="log")
    print('conn info:', conn)

    conn.execute('CREATE TABLE server_performance (ts TIMESTAMP, uid int,cpu_usage float, memory_available int, '
                 'bytes_recv int, bytes_sent int)')
    conn.close()


if __name__ == "__main__":
    create()
