import taos


def create():
    # all parameters are optional.
    # if database is specified,
    # then it must exist.
    conn = taos.connect(host="localhost",
                        port=6030,
                        database="log")
    print('client info:', conn.client_info)
    print('server info:', conn.server_info)

    conn.execute('CREATE TABLE server_performance (ts TIMESTAMP, cpu_usage float, memory_available int, '
                 'bytes_recv int, bytes_sent int)')
    conn.close()


if __name__ == "__main__":
    create()
