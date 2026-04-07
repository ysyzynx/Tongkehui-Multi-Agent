from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

def setup_cors(app: FastAPI):
    """
    配置跨域资源共享 (CORS)
    允许指定的域进行请求，避免前端跨域报错
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],  # 允许所有方法 (GET, POST, PUT, DELETE等)
        allow_headers=["*"],  # 允许所有请求头
    )
