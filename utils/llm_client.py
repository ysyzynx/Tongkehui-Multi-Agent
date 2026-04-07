import json
import base64
import requests
from pathlib import Path
from typing import Any, Optional, cast
from openai import OpenAI
import dashscope
from config.settings import settings
from utils.llm_user_context import get_llm_runtime_overrides

RUNTIME_LLM_CONFIG_PATH = Path(__file__).resolve().parent.parent / ".runtime_llm_config.json"

LLM_PROVIDER_PRESETS: dict[str, dict[str, str]] = {
    "qwen": {
        "label": "通义千问",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-plus",
        "vision_model": "qwen-vl-max",
    },
    "volcengine": {
        "label": "火山引擎",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "model": "doubao-1-5-lite-32k-250115",
        "vision_model": "doubao-vision-pro-32k",
    },
    "hunyuan": {
        "label": "腾讯混元",
        "base_url": "https://api.hunyuan.cloud.tencent.com/v1",
        "model": "hunyuan-standard-256K",
        "vision_model": "hunyuan-vision",
    },
    "deepseek": {
        "label": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
        "vision_model": "deepseek-chat",
    },
    "wenxin": {
        "label": "百度文心",
        "base_url": "https://qianfan.baidubce.com/v2",
        "model": "ernie-4.0-8k",
        "vision_model": "ernie-4.0-8k",
    },
}

IMAGE_PROVIDER_PRESETS: dict[str, dict[str, str]] = {
    "volcengine": {
        "label": "火山引擎",
    },
    "qwen": {
        "label": "通义万相",
    },
}

class LLMClient:
    """大模型调用封装工具类，解耦大模型调用与具体Agent逻辑"""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: Optional[str] = None, vision_model: Optional[str] = None):
        # 文本默认采用通义千问，绘画默认采用火山引擎（若存在运行时配置文件则按运行时配置覆盖）
        qwen_preset = LLM_PROVIDER_PRESETS["qwen"]

        self.text_provider = "qwen"
        self.text_api_key = api_key or settings.OPENAI_API_KEY
        self.text_base_url = base_url or qwen_preset["base_url"]
        self.text_model = model or qwen_preset["model"]
        self.text_vision_model = vision_model or qwen_preset["vision_model"]

        self.image_provider = "volcengine"
        self.image_api_key = settings.VOLCENGINE_API_KEY or settings.OPENAI_API_KEY

        # 兼容旧代码字段
        self.provider = self.text_provider
        self.api_key = self.text_api_key
        self.base_url = self.text_base_url
        self.model = self.text_model
        self.vision_model = self.text_vision_model

        self._init_client()
        self._load_runtime_config_if_exists()

    def _init_client(self) -> None:
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def _detect_provider(self, base_url: str) -> str:
        normalized = (base_url or "").strip().lower().rstrip("/")
        for provider, cfg in LLM_PROVIDER_PRESETS.items():
            if normalized == cfg.get("base_url", "").lower().rstrip("/"):
                return provider
        return "custom"

    def _mask_api_key(self, key: str) -> str:
        if not key:
            return ""
        if len(key) <= 8:
            return "*" * len(key)
        return f"{key[:4]}{'*' * (len(key) - 8)}{key[-4:]}"

    def _effective_text_config(self) -> dict[str, str]:
        overrides = get_llm_runtime_overrides()
        provider = str(overrides.get("text_provider") or self.text_provider or "qwen").strip().lower()
        if provider not in LLM_PROVIDER_PRESETS:
            provider = self.text_provider

        preset = LLM_PROVIDER_PRESETS.get(provider, LLM_PROVIDER_PRESETS["qwen"])
        api_key = str(overrides.get("text_api_key") or self.text_api_key or settings.OPENAI_API_KEY or "").strip()

        return {
            "provider": provider,
            "api_key": api_key,
            "base_url": preset["base_url"],
            "model": preset["model"],
            "vision_model": preset["vision_model"],
        }

    def _effective_image_config(self) -> dict[str, str]:
        overrides = get_llm_runtime_overrides()
        provider = str(overrides.get("image_provider") or self.image_provider or "volcengine").strip().lower()
        if provider not in IMAGE_PROVIDER_PRESETS:
            provider = self.image_provider

        api_key = str(
            overrides.get("image_api_key")
            or self.image_api_key
            or settings.VOLCENGINE_API_KEY
            or settings.OPENAI_API_KEY
            or ""
        ).strip()

        return {
            "provider": provider,
            "api_key": api_key,
        }

    def _build_text_client(self, config: dict[str, str]) -> OpenAI:
        return OpenAI(api_key=config["api_key"], base_url=config["base_url"])

    def _persist_runtime_config(self) -> None:
        payload = {
            "provider": self.text_provider,
            "api_key": self.text_api_key,
            "base_url": self.text_base_url,
            "model": self.text_model,
            "vision_model": self.text_vision_model,
            "text": {
                "provider": self.text_provider,
                "api_key": self.text_api_key,
                "base_url": self.text_base_url,
                "model": self.text_model,
                "vision_model": self.text_vision_model,
            },
            "image": {
                "provider": self.image_provider,
                "api_key": self.image_api_key,
            },
        }
        RUNTIME_LLM_CONFIG_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load_runtime_config_if_exists(self) -> None:
        try:
            if not RUNTIME_LLM_CONFIG_PATH.exists():
                return
            raw = RUNTIME_LLM_CONFIG_PATH.read_text(encoding="utf-8")
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                return

            text_cfg = payload.get("text") if isinstance(payload.get("text"), dict) else {}
            image_cfg = payload.get("image") if isinstance(payload.get("image"), dict) else {}

            provider = str(text_cfg.get("provider") or payload.get("provider") or self.text_provider)
            api_key = str(text_cfg.get("api_key") or payload.get("api_key") or self.text_api_key)
            base_url = str(text_cfg.get("base_url") or payload.get("base_url") or self.text_base_url)
            model = str(text_cfg.get("model") or payload.get("model") or self.text_model)
            vision_model = str(text_cfg.get("vision_model") or payload.get("vision_model") or self.text_vision_model)

            image_provider = str(image_cfg.get("provider") or self.image_provider)
            image_api_key = str(image_cfg.get("api_key") or self.image_api_key)

            if api_key and base_url and model:
                self.text_provider = provider
                self.text_api_key = api_key
                self.text_base_url = base_url
                self.text_model = model
                self.text_vision_model = vision_model
                self.image_provider = image_provider if image_provider in IMAGE_PROVIDER_PRESETS else self.image_provider
                self.image_api_key = image_api_key or self.image_api_key

                self.provider = self.text_provider
                self.api_key = self.text_api_key
                self.base_url = self.text_base_url
                self.model = self.text_model
                self.vision_model = self.text_vision_model

                self._init_client()
        except Exception:
            # 忽略本地配置损坏，回退到环境变量默认值
            return

    def get_provider_options(self) -> list[dict[str, str]]:
        options: list[dict[str, str]] = []
        for provider, cfg in LLM_PROVIDER_PRESETS.items():
            options.append({
                "provider": provider,
                "label": cfg["label"],
                "base_url": cfg["base_url"],
                "default_model": cfg["model"],
                "default_vision_model": cfg["vision_model"],
            })
        return options

    def get_image_provider_options(self) -> list[dict[str, str]]:
        options: list[dict[str, str]] = []
        for provider, cfg in IMAGE_PROVIDER_PRESETS.items():
            options.append({
                "provider": provider,
                "label": cfg["label"],
            })
        return options

    def get_image_runtime_config(self) -> dict[str, Any]:
        effective = self._effective_image_config()
        return {
            "provider": effective["provider"],
            "provider_label": IMAGE_PROVIDER_PRESETS.get(effective["provider"], {}).get("label", "火山引擎"),
            "has_api_key": bool(effective["api_key"]),
            "api_key_masked": self._mask_api_key(effective["api_key"]),
            "api_key": effective["api_key"],
        }

    def get_runtime_config(self) -> dict[str, Any]:
        effective_text = self._effective_text_config()
        effective_image = self._effective_image_config()
        return {
            "provider": effective_text["provider"],
            "provider_label": LLM_PROVIDER_PRESETS.get(effective_text["provider"], {}).get("label", "通义千问"),
            "base_url": effective_text["base_url"],
            "model": effective_text["model"],
            "vision_model": effective_text["vision_model"],
            "has_api_key": bool(effective_text["api_key"]),
            "api_key_masked": self._mask_api_key(effective_text["api_key"]),
            "text": {
                "provider": effective_text["provider"],
                "provider_label": LLM_PROVIDER_PRESETS.get(effective_text["provider"], {}).get("label", "通义千问"),
                "base_url": effective_text["base_url"],
                "model": effective_text["model"],
                "vision_model": effective_text["vision_model"],
                "has_api_key": bool(effective_text["api_key"]),
                "api_key_masked": self._mask_api_key(effective_text["api_key"]),
            },
            "image": {
                "provider": effective_image["provider"],
                "provider_label": IMAGE_PROVIDER_PRESETS.get(effective_image["provider"], {}).get("label", "火山引擎"),
                "has_api_key": bool(effective_image["api_key"]),
                "api_key_masked": self._mask_api_key(effective_image["api_key"]),
            },
            "image_provider_options": self.get_image_provider_options(),
        }

    def update_runtime_config(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        text_provider: Optional[str] = None,
        text_api_key: Optional[str] = None,
        image_provider: Optional[str] = None,
        image_api_key: Optional[str] = None,
    ) -> dict[str, Any]:
        effective_text_provider = (text_provider or provider or self.text_provider or "qwen").strip().lower()
        if effective_text_provider not in LLM_PROVIDER_PRESETS:
            raise ValueError(f"不支持的文本LLM供应商: {effective_text_provider}")

        effective_text_api_key = (text_api_key or api_key or "").strip() or self.text_api_key or settings.OPENAI_API_KEY
        if not effective_text_api_key:
            raise ValueError("文本 API Key 不能为空")

        effective_image_provider = (image_provider or self.image_provider or "volcengine").strip().lower()
        if effective_image_provider not in IMAGE_PROVIDER_PRESETS:
            raise ValueError(f"不支持的绘画LLM供应商: {effective_image_provider}")

        effective_image_api_key = (image_api_key or "").strip() or self.image_api_key or settings.VOLCENGINE_API_KEY or effective_text_api_key
        if not effective_image_api_key:
            raise ValueError("绘画 API Key 不能为空")

        preset = LLM_PROVIDER_PRESETS[effective_text_provider]
        self.text_provider = effective_text_provider
        self.text_api_key = effective_text_api_key
        self.text_base_url = preset["base_url"]
        self.text_model = preset["model"]
        self.text_vision_model = preset["vision_model"]

        self.image_provider = effective_image_provider
        self.image_api_key = effective_image_api_key

        self.provider = self.text_provider
        self.api_key = self.text_api_key
        self.base_url = self.text_base_url
        self.model = self.text_model
        self.vision_model = self.text_vision_model
        self._init_client()
        self._persist_runtime_config()
        return self.get_runtime_config()

    def generate_text(self, system_prompt: str, user_prompt: str) -> str:
        """调用大模型，返回纯文本字符串(适用于生成HTML源码等长文本)"""
        try:
            text_cfg = self._effective_text_config()
            client = self._build_text_client(text_cfg)
            response = client.chat.completions.create(
                model=text_cfg["model"],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
            )
            raw_content = response.choices[0].message.content
            content = (raw_content or "").strip()
            # 如果大模型习惯性套Markdown块，则移除
            if content.startswith("```html"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
                
            return content.strip()
        except Exception as e:
            return f"<!-- 生成失败: {str(e)} -->"

    def generate_json(self, system_prompt: str, user_prompt: str) -> dict:
        """调用大模型，强制期望返回可解析的JSON数据"""
        try:
            text_cfg = self._effective_text_config()
            client = self._build_text_client(text_cfg)
            response = client.chat.completions.create(
                model=text_cfg["model"],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
            )
            
            raw_content = response.choices[0].message.content
            content = (raw_content or "").strip()
            
            # 简单清洗部分模型自带的 markdown 符号
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
                
            return json.loads(content.strip())
        except Exception as e:
            # 异常时返回指定结构的错误对象，由外部组装到标准接口的 data 字段中
            return {"error": f"LLM API Call failed: {str(e)}", "title": "生成失败", "content": "内容生成过程中出现异常，请检查API配置或稍后重试。"}

    def generate_embedding(self, text: str) -> list[float]:
        """生成向量嵌入；失败时返回空列表，调用方可自动降级到关键词检索。"""
        try:
            payload = (text or "").strip()
            if not payload:
                return []

            text_cfg = self._effective_text_config()
            client = self._build_text_client(text_cfg)
            response = client.embeddings.create(
                model=settings.EMBEDDING_MODEL,
                input=payload,
            )
            vector = response.data[0].embedding if response.data else []
            if isinstance(vector, list):
                return vector
            return []
        except Exception:
            return []

    def generate_image(self, prompt: str) -> str:
        """调用文生图模型生成图片，返回图片URL"""
        try:
            image_cfg = self._effective_image_config()
            image_provider = image_cfg["provider"]
            image_api_key = image_cfg["api_key"]

            if image_provider == "volcengine":
                image_client = OpenAI(
                    api_key=image_api_key,
                    base_url="https://ark.cn-beijing.volces.com/api/v3",
                )
                response = image_client.images.generate(
                    model=settings.VOLCENGINE_IMAGE_MODEL,
                    prompt=prompt,
                )
                return response.data[0].url

            # qwen 通义万相
            dashscope.api_key = image_api_key
            rsp = dashscope.ImageSynthesis.call(
                model=dashscope.ImageSynthesis.Models.wanx_v1,
                prompt=prompt,
                n=1,
                size='1024*1024'
            )

            if rsp.status_code == 200:
                return rsp.output.results[0].url

            print(f"[绘画调用失败] 错误代码：{rsp.code}，信息：{rsp.message}")
            return f"https://placehold.co/1024x1024/png?text=API+Error"
        except Exception as e:
            # 万一产生异常，为了避免流程中断，返回占位图片
            print(f"[绘画调用异常] 降级使用占位图。错误信息：{str(e)}")
            return f"https://placehold.co/1024x1024/png?text=Exception"

    def _image_url_to_base64(self, image_url: str) -> str:
        """将图片URL转换为base64编码"""
        try:
            if image_url.startswith('data:image'):
                return image_url
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            image_base64 = base64.b64encode(response.content).decode('utf-8')
            return f"data:image/jpeg;base64,{image_base64}"
        except Exception as e:
            print(f"[图片转base64失败] {str(e)}")
            return ""

    def analyze_image(self, system_prompt: str, user_prompt: str, image_url: str) -> dict:
        """
        使用视觉大模型分析图片，返回JSON格式结果
        支持传入图片URL进行视觉理解
        """
        try:
            image_base64 = self._image_url_to_base64(image_url) if image_url else ""

            messages: list[dict[str, Any]] = [
                {"role": "system", "content": system_prompt}
            ]

            if image_base64:
                messages.append({
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {"type": "image_url", "image_url": {"url": image_base64}}
                    ]
                })
            else:
                messages.append({"role": "user", "content": user_prompt})

            text_cfg = self._effective_text_config()
            client = self._build_text_client(text_cfg)
            response = client.chat.completions.create(
                model=text_cfg["vision_model"],
                messages=cast(Any, messages),
                temperature=0.3,
            )

            raw_content = response.choices[0].message.content or ""
            content = raw_content.strip()

            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]

            return json.loads(content.strip())
        except Exception as e:
            print(f"[视觉分析失败] {str(e)}")
            return {"error": str(e), "status": "failed"}

    def analyze_multiple_images(self, system_prompt: str, user_prompt: str, image_urls: list[str]) -> dict:
        """
        同时分析多张图片（用于人物一致性对比等）
        """
        try:
            messages: list[dict[str, Any]] = [
                {"role": "system", "content": system_prompt}
            ]

            content_list: list[dict[str, Any]] = [{"type": "text", "text": user_prompt}]
            for image_url in image_urls:
                if image_url:
                    image_base64 = self._image_url_to_base64(image_url)
                    if image_base64:
                        content_list.append({
                            "type": "image_url",
                            "image_url": {"url": image_base64}
                        })

            messages.append({"role": "user", "content": content_list})

            text_cfg = self._effective_text_config()
            client = self._build_text_client(text_cfg)
            response = client.chat.completions.create(
                model=text_cfg["vision_model"],
                messages=cast(Any, messages),
                temperature=0.3,
            )

            raw_content = response.choices[0].message.content or ""
            content = raw_content.strip()

            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]

            return json.loads(content.strip())
        except Exception as e:
            print(f"[多图分析失败] {str(e)}")
            return {"error": str(e), "status": "failed"}


llm_client = LLMClient()
