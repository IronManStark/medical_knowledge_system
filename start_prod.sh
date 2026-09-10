#!/bin/bash

APP_NAME="医学知识库系统"
APP_DIR=$(cd "$(dirname "$0")" && pwd)
PID_FILE="$APP_DIR/mks.pid"
LOG_FILE="$APP_DIR/logs/mks.log"
PORT=5001

echo "========================================"
echo "    $APP_NAME - 生产环境启动脚本"
echo "========================================"

mkdir -p "$APP_DIR/logs"

echo "[1/3] 检查端口占用..."
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "      端口 $PORT 已被占用，正在关闭..."
    PIDS=$(lsof -Pi :$PORT -sTCP:LISTEN -t)
    for pid in $PIDS; do
        echo "      关闭进程 $pid..."
        kill -9 $pid 2>/dev/null
    done
    sleep 2
    
    if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "      警告：端口 $PORT 仍被占用，请手动检查"
    else
        echo "      端口 $PORT 已释放"
    fi
else
    echo "      端口 $PORT 未被占用"
fi

echo "[2/3] 检查残留进程..."
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 $PID 2>/dev/null; then
        echo "      发现残留进程 $PID，正在关闭..."
        kill -9 $PID 2>/dev/null
        sleep 1
    fi
    rm -f "$PID_FILE"
    echo "      残留进程已清理"
else
    echo "      无残留进程"
fi

echo "[3/3] 启动 $APP_NAME..."
cd "$APP_DIR"

export MKS_DB_TYPE=mysql
export MKS_DB_HOST=10.211.55.4
export MKS_DB_PORT=3306
export MKS_DB_USER=root
export MKS_DB_PASSWORD=Cdb930823
export MKS_DB_NAME=mks

nohup /Library/Developer/CommandLineTools/usr/bin/python3 app.py > "$LOG_FILE" 2>&1 &
PID=$!
echo $PID > "$PID_FILE"

sleep 3

if kill -0 $PID 2>/dev/null; then
    echo ""
    echo "========================================"
    echo "    $APP_NAME 启动成功！"
    echo "========================================"
    echo "  进程ID: $PID"
    echo "  运行端口: $PORT"
    echo "  访问地址: http://127.0.0.1:$PORT"
    echo "  日志文件: $LOG_FILE"
    echo "  数据库: MySQL (10.211.55.4:3306/mks)"
    echo "========================================"
else
    echo ""
    echo "========================================"
    echo "    $APP_NAME 启动失败！"
    echo "========================================"
    echo "  日志内容:"
    tail -20 "$LOG_FILE"
    echo "========================================"
    rm -f "$PID_FILE"
    exit 1
fi
