# srs_verify算法服务镜像(GPU): 一致性校验三态裁决 + 证据提纯
# 构建: docker build -t srs-verify:1.0 .
# 运行: docker run --gpus all -p 8400:8400 -v $(pwd)/models:/app/models srs-verify:1.0
FROM python:3.12-slim

WORKDIR /app

# 系统依赖(gomp/gcc运行库)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 && rm -rf /var/lib/apt/lists/*

# Python依赖: torch CPU默认镜像(GPU版见README说明换cu128轮子)
RUN pip install --no-cache-dir \
    "torch>=2.4" "transformers>=4.40" "numpy" \
    "fastapi>=0.110" "uvicorn>=0.29" pydantic

# 算法包(源码安装, 快速迭代: 挂载覆盖)
COPY srs_verify /app/srs_verify
COPY service /app/service
COPY README.md /app/README.md

# 部署契约: models/与运行目录同级(volume挂载或COPY)
# models/nli/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7
# models/embedding/bge-large-zh-v1.5 (可选, 召回用)
VOLUME /app/models

EXPOSE 8400

# 启动: uvicorn(FastAPI startup钩子预热NLI引擎, 首次加载~35s移到启动期)
CMD ["uvicorn", "service.app:app", "--host", "0.0.0.0", "--port", "8400"]
