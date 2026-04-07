import json
from openai import OpenAI
import dashscope
from config.settings import settings

class LLMClient:
    """大模型调用封装工具类，支持多API-Key和多模型切换"""
    def __init__(self, api_key=None, base_url=None, model=None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.base_url = base_url or settings.OPENAI_API_BASE
        self.model = model or settings.LLM_MODEL
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

    def generate_text(self, system_prompt: str, user_prompt: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
            )
            raw_content = response.choices[0].message.content
            content = (raw_content or "").strip()
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
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
            )
            raw_content = response.choices[0].message.content
            content = (raw_content or "").strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            return json.loads(content.strip())
        except Exception as e:
            return {"error": f"LLM API Call failed: {str(e)}", "title": "生成失败", "content": "内容生成过程中出现异常，请检查API配置或稍后重试。"}

    def generate_image(self, prompt: str, api_key=None, provider: str = "volcengine") -> str:
        try:
            provider_key = (provider or "volcengine").strip().lower()
            if provider_key == "volcengine":
                final_key = api_key or settings.VOLCENGINE_API_KEY
                if not final_key:
                    raise ValueError("volcengine 绘图 API Key 为空")
                # 使用传入的火山引擎豆包 API-Key 调用生图（基于 OpenAI 兼容格式）
                # 注意：火山引擎 API 通常需要将 model 设定为对应的 Endpoint ID（如 ep-xxx）
                # 这里默认填写一般对应的模型名或占位，如有具体 Endpoint ID 请替换
                image_client = OpenAI(
                    api_key=final_key,
                    base_url="https://ark.cn-beijing.volces.com/api/v3"
                )
                response = image_client.images.generate(
                    model=settings.VOLCENGINE_IMAGE_MODEL,
                    prompt=prompt
                )
                return response.data[0].url or ""

            # 默认使用阿里云通义万相
            dashscope.api_key = api_key or settings.OPENAI_API_KEY
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
            print(f"[绘画调用异常] 降级使用占位图。错误信息：{str(e)}")
            return f"https://placehold.co/1024x1024/png?text=Exception"
