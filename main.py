from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import traceback
from sqlalchemy import text
from config.settings import settings
from utils.database import Base, engine
from utils.deepsearch_client import deepsearch_client
from utils.auth import get_current_user
from models import models

# 加载路由
from router import story_router, check_router, reader_router, illustrator_router, literature_router, publisher_router, fact_router, illustration_review_router, knowledge_router, kg_router, kg_visualizer_router
import router as router_pkg

# 1. 自动映射创建数据库表 (通过 SQLAlchemy，如果在开发阶段可由引擎自动建表)
Base.metadata.create_all(bind=engine)

# 2. 初始化应用实例
app = FastAPI(
    title="童科绘 (AI-Assisted Sci-Pop Creator)",
    description="多智能体协作的Web端AI辅助科普内容创作平台 API 接口文档",
    version="1.0.0"
)

# 3. 设置 CORS 跨域配置 (支持前端跨域直接联调)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加异常处理器，显示详细错误
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_detail = {
        "error": str(exc),
        "traceback": traceback.format_exc(),
        "path": str(request.url)
    }
    logging.error(f"Unhandled exception: {error_detail}")
    return JSONResponse(
        status_code=500,
        content={
            "code": 500,
            "msg": "Internal Server Error",
            "error": str(exc),
            "traceback": traceback.format_exc()
        }
    )

# 4. 注册蓝图 (路由)
app.include_router(router_pkg.auth_router, prefix="/api")
auth_dep = [Depends(get_current_user)]
app.include_router(story_router, prefix="/api", dependencies=auth_dep)
app.include_router(literature_router, prefix="/api", dependencies=auth_dep)
app.include_router(check_router, prefix="/api", dependencies=auth_dep)
app.include_router(reader_router, prefix="/api", dependencies=auth_dep)
app.include_router(illustrator_router, prefix="/api", dependencies=auth_dep)
app.include_router(illustration_review_router, prefix="/api", dependencies=auth_dep)
app.include_router(publisher_router, prefix="/api", dependencies=auth_dep)
app.include_router(fact_router, prefix="/api", dependencies=auth_dep)
app.include_router(knowledge_router, prefix="/api", dependencies=auth_dep)
app.include_router(kg_router, prefix="/api")
app.include_router(kg_visualizer_router)  # 不需要认证，直接访问
app.include_router(router_pkg.llm_config_router, prefix="/api", dependencies=auth_dep)

logger = logging.getLogger("tongkehui.startup")


@app.on_event("startup")
def startup_db_self_check():
    """启动时验证数据库连接可用性，避免服务在不可用数据库上继续运行。"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("[DB SelfCheck] success: database connection is healthy")
    except Exception as exc:
        logger.error("[DB SelfCheck] failed: %s", exc)
        raise RuntimeError(f"数据库连通性检查失败，请检查 DATABASE_URL 与数据库服务状态: {exc}") from exc


@app.on_event("startup")
def startup_self_check():
    if not settings.DEEPSEARCH_SELF_CHECK:
        return

    status = deepsearch_client.runtime_status()
    logger.warning(
        "[DeepSearch SelfCheck] enabled=%s model=%s base=%s enable_search=%s key=%s",
        status.get("enabled"),
        status.get("model"),
        status.get("base"),
        status.get("enable_search"),
        status.get("key_mask"),
    )

@app.get("/", tags=["Health"])
def health_check():
    """基础健康检查接口"""
    return {"code": 200, "msg": "API is running normally.", "data": {"status": "ok"}}

if __name__ == "__main__":
    import uvicorn
    # 本地启动命令： python main.py
    # 后期建议用命令启动: uvicorn main:app --reload --host 0.0.0.0 --port 8000
    uvicorn.run(
        "main:app", 
        host=settings.HOST, 
        port=settings.PORT, 
        reload=settings.DEBUG
    )
