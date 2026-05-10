# 使用 Python 3.11 轻量版作为基础镜像
# slim 版本比完整版小很多，但包含了运行 Python 所需的基本依赖
FROM python:3.11-slim

# 设置工作目录 — 容器内的 /app 目录
WORKDIR /app

# 先复制 requirements.txt 并安装依赖
# 这样做可以利用 Docker 的层缓存：如果 requirements.txt 没变，
# 就不会重新安装依赖，加快构建速度
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制所有应用代码到容器
COPY . .

# 暴露 8000 端口（FastAPI 默认端口）
# 这只是文档性质的声明，实际端口映射在 docker-compose.yml 中配置
EXPOSE 8000

# 启动命令 — 使用 uvicorn 运行 FastAPI 应用
# --host 0.0.0.0 表示监听所有网络接口（不只是 localhost）
# --port 8000 指定端口号
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
