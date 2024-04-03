import  sys
import shutil
import socket
hostname = socket.gethostname()
# 读取自定义参数对
def read_key_value_file(file_path):
    key_value_dict = {}
    with open(file_path, 'r') as file:
        for line in file:
            line = line.strip()  # 去除行尾的换行符
            if not line or line.startswith('#'):  # 忽略空行和注释行
                continue
            key, value = line.split()  # 假设键值对之间有空格分隔
            key_value_dict[key] = value
    return key_value_dict


# 替换或添加行到文件B中
def process_file_b(file_a_path, file_b_path, output_path):
    key_value_dict = read_key_value_file(file_a_path)
    keys_to_add = set(key_value_dict.keys())  # 存储需要添加到文件末尾的键
    output = open(output_path, 'w')
    with open(file_b_path, 'r') as file_b:
        for line in file_b:
            for key in key_value_dict:
                if line.startswith('# ' + key):
                    # 如果行以'# ' + key开头，则替换为文件A中对应的内容
                    replacement_line = key + f" {key_value_dict[key]}\n"
                    output.write(replacement_line)
                    keys_to_add.discard(key)  # 从需要添加的键集合中移除已替换的键
                    break
            else:
                # 对于其他行，直接复制到输出文件
                output.write(line)

    # 将未找到的键值对添加到输出文件末尾
    for key in keys_to_add:
        output.write(f"{key} {key_value_dict[key]}\n")
    output.write("monitorFqdn " + hostname)

# 调用函数
file_a_path = sys.argv[1]       # 参数1: 自定义参数对
file_b_path = sys.argv[2]       # 参数2: 配置模板源文件
output_path = '/tmp/taos.cfg'   # 临时输出文件的路径，最后将临时文件覆盖到tdengine配置

process_file_b(file_a_path, file_b_path, output_path)
shutil.copy2(output_path, "/etc/taos/taos.cfg") # 覆盖tdengine配置
