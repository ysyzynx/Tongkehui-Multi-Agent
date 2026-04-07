from typing import Dict, Any, List, Union
import json
import re
from agent.base_agent import BaseAgent
from utils.llm_client import llm_client
from prompts.illustrator_prompt import (
    ILLUSTRATOR_SYSTEM_PROMPT,
    ILLUSTRATOR_USER_PROMPT_TEMPLATE,
    IMAGE_REGENERATE_PROMPT,
)

class IllustratorAgent(BaseAgent):
    """插画师Agent：根据故事内容切分场景并生成AI绘画提示词"""

    def __init__(self):
        super().__init__(name="Illustrator", description="Divides text into scenes and generates illustration prompts.")
        self.system_prompt = ILLUSTRATOR_SYSTEM_PROMPT

    def _is_heading_line(self, line: str) -> bool:
        text = (line or "").strip()
        return bool(re.match(r"^第[一二三四五六七八九十百千万零两〇0-9]+(?:章|节|部分|幕|回)", text))

    def _is_title_meta_line(self, line: str) -> bool:
        text = (line or "").strip()
        return bool(re.match(r"^[\[【(（]?\s*标题\s*[\]】)）]?\s*[：:].*", text))

    def _split_semantic_units(self, content: str) -> List[str]:
        units: List[str] = []
        paragraph_buffer: List[str] = []
        current_heading = ""

        def flush_paragraph() -> None:
            nonlocal paragraph_buffer
            if not paragraph_buffer:
                return
            paragraph = "".join(paragraph_buffer).strip()
            paragraph_buffer = []
            if not paragraph:
                return
            if current_heading:
                units.append(f"{current_heading}\n{paragraph}")
            else:
                units.append(paragraph)

        for raw in (content or "").splitlines():
            line = raw.strip()
            if not line:
                flush_paragraph()
                continue
            if self._is_title_meta_line(line):
                continue
            if self._is_heading_line(line):
                flush_paragraph()
                current_heading = line
                continue
            paragraph_buffer.append(line)

        flush_paragraph()

        if not units and (content or "").strip():
            units = [re.sub(r"\s+", "", content.strip())]
        return units

    def _split_long_unit(self, unit: str, max_len: int) -> List[str]:
        if len(unit) <= max_len:
            return [unit]

        sentence_like = [s.strip() for s in re.split(r"(?<=[。！？!?；;])", unit) if s.strip()]
        if len(sentence_like) <= 1:
            return [unit[i:i + max_len] for i in range(0, len(unit), max_len)]

        parts: List[str] = []
        buff = ""
        for seg in sentence_like:
            if not buff:
                buff = seg
                continue
            if len(buff) + len(seg) <= max_len:
                buff += seg
            else:
                parts.append(buff)
                buff = seg
        if buff:
            parts.append(buff)
        return parts

    def _balanced_semantic_chunks(self, story_content: str, image_count: int) -> List[str]:
        target_count = max(1, image_count)
        units = self._split_semantic_units(story_content)

        if not units:
            return [""] * target_count

        total_len = sum(len(u) for u in units)
        target_len = max(120, total_len // target_count)

        expanded_units: List[str] = []
        for unit in units:
            expanded_units.extend(self._split_long_unit(unit, int(target_len * 1.25)))

        units = expanded_units

        if len(units) < target_count:
            while len(units) < target_count:
                idx = max(range(len(units)), key=lambda i: len(units[i]))
                source = units[idx]
                if len(source) <= 2:
                    units.append(source)
                    continue
                cut = len(source) // 2
                left = source[:cut].strip()
                right = source[cut:].strip()
                units[idx] = left or source
                units.insert(idx + 1, right or source)

        groups: List[List[str]] = []
        current_group: List[str] = []
        current_len = 0
        i = 0
        while i < len(units):
            remaining_units = len(units) - i
            remaining_groups = target_count - len(groups)

            if remaining_groups <= 0:
                break

            unit = units[i]
            unit_len = len(unit)

            must_close = current_group and (remaining_units == remaining_groups)
            should_close = current_group and current_len + unit_len > target_len and remaining_groups > 1

            if must_close or should_close:
                groups.append(current_group)
                current_group = []
                current_len = 0
                continue

            current_group.append(unit)
            current_len += unit_len
            i += 1

        if current_group:
            groups.append(current_group)

        merged = ["\n\n".join(group).strip() for group in groups if group]

        while len(merged) > target_count:
            idx = min(range(len(merged) - 1), key=lambda x: len(merged[x]) + len(merged[x + 1]))
            merged[idx] = f"{merged[idx]}\n\n{merged[idx + 1]}".strip()
            del merged[idx + 1]

        while len(merged) < target_count:
            idx = max(range(len(merged)), key=lambda x: len(merged[x]))
            text = merged[idx]
            if len(text) <= 2:
                merged.append(text)
                continue
            cut = len(text) // 2
            left = text[:cut].strip()
            right = text[cut:].strip()
            merged[idx] = left or text
            merged.insert(idx + 1, right or text)

        return merged[:target_count]

    def _normalize_art_style(self, art_style: str) -> str:
        style_text = (art_style or "").strip()
        if not style_text:
            return "卡通风格"

        lower = style_text.lower()
        if "3d" in lower or "三维" in style_text:
            return "3D渲染风格"
        if "水彩" in style_text:
            return "水彩画风格"
        if "儿童绘画" in style_text or "儿童" in style_text:
            return "儿童绘画风格"
        if "写真" in style_text or "写实" in style_text:
            return "写真风格"
        if "卡通" in style_text:
            return "卡通风格"

        return style_text if style_text.endswith("风格") else f"{style_text}风格"

    def _remove_style_words(self, text: str) -> str:
        cleaned = str(text or "")
        style_pattern = re.compile(
            r"(卡通(?:风格)?|儿童绘画(?:风格)?|水彩画?(?:风格)?|写真(?:风格)?|写实(?:风格)?|3D渲染(?:风格)?|三维渲染(?:风格)?)",
            re.IGNORECASE,
        )
        cleaned = style_pattern.sub("", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" ，,；;。")
        return cleaned

    def run(self, story_content: str, image_count: int = 4, art_style: str = "卡通", extra_requirements: str = "") -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """
        根据文本内容，拆分图片并生成相应的 Prompts 画图建议。最后模拟/实际调用生图能力。
        """
        # 将用户指定的风格动态注入到系统提示词里
        dynamic_system_prompt = self.system_prompt.replace(
            "儿童绘本插画风格",
            f"{art_style}风格"
        )

        extra_prompt_text = ""
        if extra_requirements:
            extra_prompt_text = f"\n【用户指定的额外绘画要求（你必须将其融合进所有image_prompt中）】：{extra_requirements}\n"

        semantic_chunks = self._balanced_semantic_chunks(story_content, image_count)
        chunk_payload = [{"scene_id": idx + 1, "text_chunk": chunk} for idx, chunk in enumerate(semantic_chunks)]
        chunk_payload_json = json.dumps(chunk_payload, ensure_ascii=False, indent=2)

        user_prompt = ILLUSTRATOR_USER_PROMPT_TEMPLATE.format(
            image_count=image_count,
            art_style=art_style,
            extra_prompt_text=extra_prompt_text,
            chunk_payload_json=chunk_payload_json,
        )

        # 1. 调用 LLM 根据文章生成分镜拆分和提示词
        scene_data = llm_client.generate_json(dynamic_system_prompt, user_prompt)

        # 为了容错，如果返回的是字典带有 error，说明失败了
        if isinstance(scene_data, dict) and "error" in scene_data:
            return scene_data

        # 兜底修正：确保数量和 text_chunk 稳定，防止模型偏离要求。
        if not isinstance(scene_data, list):
            scene_data = []

        fixed_scenes: List[Dict[str, Any]] = []
        for idx, chunk in enumerate(semantic_chunks):
            model_scene = scene_data[idx] if idx < len(scene_data) and isinstance(scene_data[idx], dict) else {}
            prompt = (model_scene.get("image_prompt") or "").strip()
            if not prompt:
                prompt = f"根据文本绘制关键场景：{chunk[:80]}，{art_style}风格"
            if not prompt.endswith(f"，{art_style}风格"):
                prompt = f"{prompt}，{art_style}风格"

            fixed_scenes.append({
                "scene_id": idx + 1,
                "text_chunk": chunk,
                "summary": (model_scene.get("summary") or chunk[:40]).strip(),
                "image_prompt": prompt,
            })

        scene_data = fixed_scenes

        # 2. 调用生图能力（这里配合 llm_client 中的 image 接口）
        image_runtime = llm_client.get_image_runtime_config()
        image_provider = str(image_runtime.get("provider") or "volcengine").strip().lower()
        image_api_key = str(image_runtime.get("api_key") or "").strip()
        if not image_api_key:
            return {"error": "绘画 API Key 未配置，无法调用绘图模型。"}

        for scene in scene_data:
            prompt = scene.get("image_prompt", "")
            if prompt:
                from utils.llm_client_multi import LLMClient
                image_llm = LLMClient(api_key=image_api_key)
                image_url = image_llm.generate_image(prompt, api_key=image_api_key, provider=image_provider)
                scene["image_url"] = image_url

        self.result = scene_data
        return self.result

    def regenerate_image(self, image_prompt: str, feedback: str, art_style: str = "卡通", extra_requirements: str = "") -> Dict[str, str]:
        """
        根据用户修改意见重写提示词并重新生成图片。
        """
        normalized_style = self._normalize_art_style(art_style)
        style_name = normalized_style[:-2] if normalized_style.endswith("风格") else normalized_style
        cleaned_image_prompt = self._remove_style_words(image_prompt)

        requirement_lines = []
        if extra_requirements:
            requirement_lines.append(f"5. 额外要求：{extra_requirements}")
        requirement_lines.append(f"6. 画风锁定：最终提示词只能使用“{normalized_style}”，不得出现其他画风词。")
        extra_requirements_text = "\n" + "\n".join(requirement_lines)

        revise_prompt = IMAGE_REGENERATE_PROMPT.format(
            image_prompt=cleaned_image_prompt,
            feedback=feedback,
            art_style=style_name,
            extra_requirements_text=extra_requirements_text,
        )

        revised_prompt = llm_client.generate_text("你是严谨的提示词优化助手。", revise_prompt).strip()
        revised_prompt = self._remove_style_words(revised_prompt)
        revised_prompt = revised_prompt.strip(" ，,；;。")
        revised_prompt = f"{revised_prompt}，{normalized_style}"

        image_runtime = llm_client.get_image_runtime_config()
        image_provider = str(image_runtime.get("provider") or "volcengine").strip().lower()
        image_api_key = str(image_runtime.get("api_key") or "").strip()
        if not image_api_key:
            return {"error": "绘画 API Key 未配置，无法调用绘图模型。"}

        from utils.llm_client_multi import LLMClient
        image_llm = LLMClient(api_key=image_api_key)
        image_url = image_llm.generate_image(revised_prompt, api_key=image_api_key, provider=image_provider)

        return {
            "image_prompt": revised_prompt,
            "image_url": image_url,
        }
