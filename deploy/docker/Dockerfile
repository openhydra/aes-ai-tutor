FROM python:3.11
WORKDIR /root

# 环境变量
ENV AITUTOR_ROOT=/root/aitutor_data

# 初始化环境
RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && \
    echo "Asia/Shanghai" > /etc/timezone
RUN apt-get update -y && \
    apt-get install -y git vim && \
    apt-get install -y --no-install-recommends libgl1 libglib2.0-0 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
RUN pip install --upgrade pip setuptools
RUN pip install --index-url https://pypi.python.org/simple/ pipx && \
    pipx install poetry --force

# Add poetry to PATH
ENV PATH="/root/.local/bin:${PATH}"

COPY ./libs /root/aes-ai-tutor/libs

# 安装依赖
WORKDIR /root/aes-ai-tutor/libs
RUN poetry config virtualenvs.create false && \
    poetry lock --no-update
RUN poetry install --with lint,test


# 初始化配置
WORKDIR /root/aes-ai-tutor/libs/aitutor

# 初始化知识库文件
ADD ./deploy/docker/data.tar.gz $AITUTOR_ROOT/
