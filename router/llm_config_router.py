from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from models import models
from models import schemas
from utils.database import get_db
from utils.auth import get_current_user
from utils.llm_user_context import set_llm_runtime_overrides
from utils.response import success, error
from utils.llm_client import llm_client

router = APIRouter(prefix="/llm-config", tags=["LLM 配置"])


@router.get("/options", summary="获取支持的LLM供应商")
def get_llm_options():
    text_options = llm_client.get_provider_options()
    image_options = llm_client.get_image_provider_options()
    return success({"options": text_options, "text_options": text_options, "image_options": image_options}, msg="获取LLM供应商成功")


@router.get("/current", summary="获取当前LLM运行时配置")
def get_llm_current_config(current_user: models.User = Depends(get_current_user)):
    return success(llm_client.get_runtime_config(), msg="获取当前LLM配置成功")


@router.post("/update", summary="更新LLM运行时配置")
def update_llm_runtime_config(
    req: schemas.LLMConfigUpdateRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    try:
        text_provider = (req.text_provider or req.provider or current_user.llm_text_provider or "qwen").strip().lower()
        if text_provider not in {"qwen", "volcengine", "hunyuan", "deepseek", "wenxin"}:
            raise ValueError(f"不支持的文本LLM供应商: {text_provider}")

        image_provider = (req.image_provider or current_user.llm_image_provider or "volcengine").strip().lower()
        if image_provider not in {"volcengine", "qwen"}:
            raise ValueError(f"不支持的绘画LLM供应商: {image_provider}")

        text_api_key = (req.text_api_key or req.api_key or current_user.llm_text_api_key or "").strip()
        image_api_key = (req.image_api_key or current_user.llm_image_api_key or text_api_key or "").strip()

        if not text_api_key:
            raise ValueError("文本 API Key 不能为空")
        if not image_api_key:
            raise ValueError("绘画 API Key 不能为空")

        current_user.llm_text_provider = text_provider
        current_user.llm_text_api_key = text_api_key
        current_user.llm_image_provider = image_provider
        current_user.llm_image_api_key = image_api_key
        db.add(current_user)
        db.commit()

        set_llm_runtime_overrides(
            {
                "text_provider": text_provider,
                "text_api_key": text_api_key,
                "image_provider": image_provider,
                "image_api_key": image_api_key,
            }
        )

        data = llm_client.get_runtime_config()
        return success(data, msg="LLM配置已更新")
    except ValueError as ex:
        db.rollback()
        return error(code=400, msg=str(ex))
    except Exception as ex:
        db.rollback()
        return error(code=500, msg=f"更新LLM配置失败: {str(ex)}")
