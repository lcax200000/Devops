#!/bin/bash

# 创建 Docker volume
docker volume create tb-data
docker volume create tb-logs

# 拉取 Docker Compose 配置
docker-compose pull

# 启动 Docker 容器
docker-compose up -d

# 查看特定容器日志
docker-compose logs -f tb
