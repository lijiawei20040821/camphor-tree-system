FROM python:3.9-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建必要的目录
RUN mkdir -p uploads models logs

# 设置环境变量
ENV FLASK_ENV=production
ENV FLASK_APP=run.py

# 暴露端口
EXPOSE 5000

# 启动命令
CMD ["python", "run.py"]