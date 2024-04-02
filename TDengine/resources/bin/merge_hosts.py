import socket
import os
import  sys

print(sys.argv)

# 加载 hosts
with open(sys.argv[1], 'r') as f:
    etc_hosts_lines = f.readlines()

# 合并到 '/etc/hosts'
merge_into = '/etc/hosts'

try:
    with open(merge_into, 'r') as f:
        existing_hosts_lines = f.readlines()
except FileNotFoundError:
    existing_hosts_lines = []

# 过滤重复内容并合并两个文件的不同部分
unique_lines = set()

# 添加 existing_hosts_lines 到 unique_lines，但移除重复项
for line in existing_hosts_lines:
    unique_lines.add(line.strip())

# 添加 etc_hosts_lines 到 unique_lines，但仅当它们不重复时
for line in etc_hosts_lines:
    line_stripped = line.strip()
    if line_stripped not in unique_lines:
        unique_lines.add(line_stripped)

# 将 unique_lines 转换回列表，并按原样写入到目标文件
all_hosts_lines = [line + '\n' for line in unique_lines]

# 写入到目标文件
with open(merge_into, 'w') as f:
    f.writelines(all_hosts_lines)

# 打印出结果
with open(merge_into, 'r') as f:
    print(f.read())