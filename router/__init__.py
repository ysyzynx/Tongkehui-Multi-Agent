"""
童科绘 API 路由模块
统一管理所有 API 端点
"""

from .story_router import router as story_router
from .check_router import router as check_router
from .reader_router import router as reader_router
from .illustrator_router import router as illustrator_router
from .literature_router import router as literature_router
from .publisher_router import router as publisher_router
from .fact_router import router as fact_router
from .illustration_review_router import router as illustration_review_router
from .knowledge_router import router as knowledge_router
from .kg_router import router as kg_router
from .kg_visualizer_router import router as kg_visualizer_router
from .llm_config_router import router as llm_config_router
from .auth_router import router as auth_router

__all__ = [
    "story_router",
    "check_router",
    "reader_router",
    "illustrator_router",
    "literature_router",
    "publisher_router",
    "fact_router",
    "illustration_review_router",
    "knowledge_router",
    "kg_router",
    "kg_visualizer_router",
    "llm_config_router",
    "auth_router",
]
