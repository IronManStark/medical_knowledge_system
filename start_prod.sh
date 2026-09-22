#!/bin/bash

APP_DIR=$(cd "$(dirname "$0")" && pwd)
PID_FILE="$APP_DIR/mks.pid"
LOG_FILE="$APP_DIR/logs/mks.log"
PORT=7122

mkdir -p "$APP_DIR/logs"

echo "医学知识库系统 生产环境"

if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "端口被占了，先杀掉"
    for pid in $(lsof -Pi :$PORT -sTCP:LISTEN -t); do
        kill -9 $pid 2>/dev/null
    done
    sleep 2
    if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "端口 $PORT 还没释放，手动看一下"
    fi
fi

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 $PID 2>/dev/null; then
        echo "旧进程 $PID 还在，杀掉"
        kill -9 $PID 2>/dev/null
        sleep 1
    fi
    rm -f "$PID_FILE"
fi

echo "启动中..."
cd "$APP_DIR"

export MKS_DB_HOST=10.211.55.4
export MKS_DB_PORT=3306
export MKS_DB_USER=root
export MKS_DB_PASSWORD=Cdb930823
export MKS_DB_NAME=mks

export MKS_MINIO_ENDPOINT=10.211.55.4:9000
export MKS_MINIO_USER=admin
export MKS_MINIO_PASSWORD=Mkb.001@2023
export MKS_MINIO_BUCKET=mks
export MKS_MINIO_SECURE=false

nohup /Library/Developer/CommandLineTools/usr/bin/python3 mks_main.py > "$LOG_FILE" 2>&1 &
PID=$!
echo $PID > "$PID_FILE"

sleep 3

if kill -0 $PID 2>/dev/null; then
    echo "起来了"
    echo "地址 http://127.0.0.1:$PORT"
    echo "pid $PID"
else
    echo "没起来，日志最后几行："
    tail -20 "$LOG_FILE"
    rm -f "$PID_FILE"
    exit 1
fi
