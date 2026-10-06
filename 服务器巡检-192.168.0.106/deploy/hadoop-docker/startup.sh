#!/bin/bash
# Hadoop 伪分布式单容器启动脚本（apache/hadoop:3.3.6）
set -m

# 首次启动格式化 NameNode（有 VERSION 文件说明已格式化）
if [ ! -f /hadoop/dfs/name/current/VERSION ]; then
  echo "[startup] 首次启动：格式化 NameNode ..."
  hdfs namenode -format -nonInteractive
fi

echo "[startup] 启动 NameNode"
hdfs namenode &

# 等 NameNode RPC 就绪（最多 60s）
for i in $(seq 1 30); do
  (echo > /dev/tcp/127.0.0.1/8020) 2>/dev/null && break
  sleep 2
done

echo "[startup] 启动 DataNode"
hdfs datanode &

echo "[startup] 启动 YARN ResourceManager"
yarn resourcemanager &

echo "[startup] 启动 NodeManager"
yarn nodemanager &

echo "[startup] 启动 MapReduce JobHistoryServer"
mapred historyserver &

echo "[startup] 全部进程已拉起"
wait
