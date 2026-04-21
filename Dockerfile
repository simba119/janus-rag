FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    git \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

COPY src/ ./src/
COPY demo/ ./demo/
COPY skill/ ./skill/

EXPOSE 7860

ENV SEARCH_ADAPTER=static
ENV HF_ENDPOINT=https://hf-mirror.com

CMD ["python", "src/main.py"]