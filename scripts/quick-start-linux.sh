#!/bin/bash
# ========================================
# 童科绘 Linux 快速启动脚本（测试用）
# ========================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  童科绘快速启动${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}创建虚拟环境...${NC}"
    python3 -m venv .venv
fi

echo -e "${GREEN}激活虚拟环境...${NC}"
source .venv/bin/activate

echo -e "${GREEN}安装依赖...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

if [ ! -f ".env" ]; then
    if [ -f ".env.production" ]; then
        echo -e "${YELLOW}复制配置文件...${NC}"
        cp .env.production .env
        echo -e "${RED}请编辑 .env 填入 API keys${NC}"
    fi
fi

mkdir -p data logs

echo ""
echo -e "${GREEN}启动服务...${NC}"
echo ""
echo "前端: http://localhost:5173 (需要单独启动)"
echo "后端: http://localhost:8000"
echo "文档: http://localhost:8000/docs"
echo ""
echo "按 Ctrl+C 停止"
echo ""

uvicorn main:app --host 0.0.0.0 --port 8000 --reload
