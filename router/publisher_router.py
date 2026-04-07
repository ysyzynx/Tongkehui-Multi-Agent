import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from fastapi import APIRouter
from fastapi.responses import FileResponse

from models import schemas
from utils.pdf_generator import PDFGenerator
from utils.response import error, success

router = APIRouter(prefix="/publisher", tags=["排版发布中心 (Publisher)"])

ARTICLE_DIR = Path("article")
ARTICLE_DIR.mkdir(parents=True, exist_ok=True)


def _safe_name(name: str) -> str:
	cleaned = re.sub(r"[^\w\u4e00-\u9fa5-]+", "-", name or "story")
	cleaned = cleaned.strip("-")
	return cleaned[:60] or "story"


def _is_heading(line: str) -> bool:
	text = (line or "").strip()
	if not text:
		return False
	if text.startswith("#"):
		return True
	return bool(re.match(r"^第[一二三四五六七八九十百千万零两〇0-9]+(?:章|节|部分|幕|回)", text))


def _format_paragraph_text(text: str) -> str:
	"""
	格式化段落文本：处理标点、空格等
	"""
	import re
	result = text or ""

	# 1. 先处理引号，避免被其他转换影响
	# 将英文单引号/双引号转换为中文双引号
	# 处理成对的引号
	def replace_quotes(content):
		# 使用状态机处理引号配对
		in_quote = False
		output = []
		i = 0
		while i < len(content):
			char = content[i]
			if char in ('"', "'"):
				if not in_quote:
					# 左引号
					output.append("“")
					in_quote = True
				else:
					# 右引号
					output.append("”")
					in_quote = False
			else:
				output.append(char)
			i += 1
		# 如果还有未闭合的引号，补充右引号
		if in_quote:
			output.append("”")
		return "".join(output)

	result = replace_quotes(result)

	# 2. 清理多余的空格和换行（但保留段落结构）
	result = re.sub(r"\s+", " ", result)

	# 3. 标准化标点符号（英文标点转中文标点）
	result = result.replace(",", "，")
	result = result.replace("!", "！")
	result = result.replace("?", "？")
	result = result.replace(":", "：")
	result = result.replace(";", "；")

	# 处理句号：需要排除小数点、网址等情况
	# 只有当句号不在数字之间、不在英文单词之间时才替换
	def replace_period(match):
		before = match.group(1) or ""
		after = match.group(3) or ""
		# 如果是数字.数字（如3.14），保留原样
		if before.isdigit() and after.isdigit():
			return match.group(0)
		# 如果是英文单词（如Mr.），保留原样
		if before.isalpha() and after.isalpha():
			return match.group(0)
		# 其他情况替换为中文句号
		return before + "。" + after

	result = re.sub(r'(\S?)\.(\S?)', replace_period, result)

	# 处理括号
	result = result.replace("(", "（")
	result = result.replace(")", "）")

	# 4. 再次确保引号正确（处理可能的遗留问题）
	# 替换任何残留的直角引号为中文双引号
	result = result.replace("「", "“").replace("」", "”")
	result = result.replace("『", "“").replace("』", "”")

	# 5. 清理标点后的多余空格
	result = re.sub(r"([。！？，；：”）])\s+", r"\1", result)
	result = re.sub(r"\s+([“（])", r"\1", result)

	# 6. 中文与英文/数字之间加空格
	result = re.sub(r"([\u4e00-\u9fff])([a-zA-Z0-9])", r"\1 \2", result)
	result = re.sub(r"([a-zA-Z0-9])([\u4e00-\u9fff])", r"\1 \2", result)

	# 7. 清理开头和结尾
	result = result.strip()

	# 8. 确保段落以正确的标点结尾
	if result and not re.search(r"[。！？!?”）]$", result):
		if len(result) > 10:
			result += "。"

	return result


def _split_blocks(content: str) -> List[Dict[str, str]]:
	blocks: List[Dict[str, str]] = []
	paragraph_buffer = []

	for raw in (content or "").splitlines():
		text = raw.strip()
		if not text:
			if paragraph_buffer:
				# 合并并格式化段落
				raw_text = "".join(paragraph_buffer)
				formatted_text = _format_paragraph_text(raw_text)
				blocks.append({"type": "paragraph", "text": formatted_text})
				paragraph_buffer = []
			continue

		if _is_heading(text):
			if paragraph_buffer:
				raw_text = "".join(paragraph_buffer)
				formatted_text = _format_paragraph_text(raw_text)
				blocks.append({"type": "paragraph", "text": formatted_text})
				paragraph_buffer = []
			# 移除标题前面的 # 标记
			import re
			heading_text = re.sub(r"^#+\s*", "", text)
			blocks.append({"type": "heading", "text": heading_text})
			continue

		paragraph_buffer.append(text)

	if paragraph_buffer:
		raw_text = "".join(paragraph_buffer)
		formatted_text = _format_paragraph_text(raw_text)
		blocks.append({"type": "paragraph", "text": formatted_text})

	return blocks


def _is_trailing_resource_line(line: str) -> bool:
	text = (line or "").strip()
	if not text:
		return False
	pattern = re.compile(
		r"(?:小科学家加油站|USGS\s*Kids|NSTA|capillary\s*action|https?://|www\.|网站|学习中心|搜索|下载|资源|延伸阅读|一起做的|记录表|实验包|✅|🔗)",
		re.IGNORECASE,
	)
	return bool(pattern.search(text))


def _strip_trailing_resource_recommendations(content: str) -> str:
	lines = (content or "").splitlines()

	while lines and not lines[-1].strip():
		lines.pop()

	while lines and _is_trailing_resource_line(lines[-1]):
		lines.pop()
		while lines and not lines[-1].strip():
			lines.pop()

	return "\n".join(lines)


def _highlight_terms_in_full_text(blocks: List[Dict[str, str]], terms: List[str]) -> Tuple[List[Dict[str, str]], List[str]]:
	"""
	在全文范围内仅对词条第一次出现时进行高亮处理
	"""
	if not terms or not blocks:
		return blocks, []

	# 按词条长度从长到短排序，避免短词先匹配长词的一部分
	sorted_terms = sorted(terms, key=lambda t: -len(t))
	used_terms = set()
	highlighted_terms_in_order: List[str] = []

	result_blocks = []
	for block in blocks:
		if block["type"] == "heading":
			result_blocks.append(block)
			continue

		text = block["text"]
		for term in sorted_terms:
			if not term or term in used_terms:
				continue

			# 词条以中文为主，按字面匹配首次出现，避免边界条件过严导致漏高亮。
			pattern = re.compile(r'(' + re.escape(term) + r')')

			if pattern.search(text):
				# 使用带计数器的替换函数
				count = [0]
				def replace_func(match):
					if count[0] == 0:
						count[0] += 1
						used_terms.add(term)
						highlighted_terms_in_order.append(term)
						return f'<span class="highlight-term">{match.group(1)}</span>'
					return match.group(1)

				text = pattern.sub(replace_func, text)

		result_blocks.append({"type": "paragraph", "text": text})

	return result_blocks, highlighted_terms_in_order


def _build_scientific_explanation(term: str, content: str, existing: str = "") -> str:
	if str(existing or "").strip():
		return str(existing).strip()

	text = str(content or "").replace("\n", " ").strip()
	if not text:
		return f"{term}是文中出现的重要科学词条。建议从定义、形成机制、适用条件和典型现象四个维度理解该概念。"

	index = text.find(term)
	if index < 0:
		return f"{term}是文中出现的重要科学词条。建议从定义、形成机制、适用条件和典型现象四个维度理解该概念。"

	left = max(
		text.rfind("。", 0, index),
		text.rfind("！", 0, index),
		text.rfind("？", 0, index),
	)
	right_candidates = [
		p for p in [
			text.find("。", index),
			text.find("！", index),
			text.find("？", index),
		] if p >= 0
	]
	right = min(right_candidates) if right_candidates else min(len(text), index + len(term) + 40)
	start = 0 if left < 0 else left + 1
	context = text[start:right + 1].strip()

	if context:
		return (
			f"{term}是文中涉及的科学概念。结合语境“{context}”，"
			"可将其理解为解释相关现象或机制的关键术语，建议重点关注其定义、作用过程与适用范围。"
		)

	return f"{term}是文中出现的重要科学词条。建议从定义、形成机制、适用条件和典型现象四个维度理解该概念。"


def _align_glossary_with_highlighted_terms(
	highlighted_terms: List[str],
	glossary: List[Dict[str, str]],
	content: str,
) -> List[Dict[str, str]]:
	if not highlighted_terms:
		return []

	existing_map: Dict[str, str] = {}
	for item in glossary or []:
		term = str((item or {}).get("term", "")).strip()
		explanation = str((item or {}).get("explanation", "")).strip()
		if term and term not in existing_map:
			existing_map[term] = explanation

	aligned: List[Dict[str, str]] = []
	for term in highlighted_terms:
		if not term:
			continue
		explanation = _build_scientific_explanation(term, content, existing_map.get(term, ""))
		aligned.append({"term": term, "explanation": explanation})

	return aligned


def _build_layout_html(title: str, content: str, glossary: List[Dict[str, str]], illustrations: List[Dict[str, str]], highlight_terms: Optional[List[str]] = None, for_image: bool = False) -> str:
	cleaned_content = _strip_trailing_resource_recommendations(content)
	blocks = _split_blocks(cleaned_content)

	# 提取需要高亮的词条
	terms_to_highlight = []
	if highlight_terms and isinstance(highlight_terms, list):
		terms_to_highlight = [str(t).strip() for t in highlight_terms if str(t).strip()]
	elif glossary and isinstance(glossary, list):
		terms_to_highlight = [str(item.get("term", "")).strip() for item in glossary if str(item.get("term", "")).strip()]

	# 在全文范围内进行高亮处理（仅第一次出现）
	highlighted_terms_in_order: List[str] = []
	if terms_to_highlight:
		blocks, highlighted_terms_in_order = _highlight_terms_in_full_text(blocks, terms_to_highlight)

	# 词条表与正文高亮词条强一致：只保留实际高亮成功的词条，并为每个词条补齐科学解释。
	render_glossary = _align_glossary_with_highlighted_terms(
		highlighted_terms=highlighted_terms_in_order,
		glossary=glossary,
		content=cleaned_content,
	)

	# 获取所有段落索引
	paragraph_indexes = []
	for idx, block in enumerate(blocks):
		if block["type"] == "paragraph":
			paragraph_indexes.append(idx)

	total_paragraphs = len(paragraph_indexes)
	total_images = len(illustrations)

	# 计算每个图片应该在哪个段落后面（均匀分布策略）
	image_positions = []
	if total_images > 0 and total_paragraphs > 0:
		for img_idx in range(total_images):
			# 均匀分布：第1张图在 1/(n+1) 位置，第2张在 2/(n+1) 位置...
			ideal_ratio = (img_idx + 1) / (total_images + 1)
			ideal_paragraph_pos = int(ideal_ratio * total_paragraphs)
			# 确保在有效范围内
			ideal_paragraph_pos = max(0, min(total_paragraphs - 1, ideal_paragraph_pos))
			# 获取对应的 block index
			image_block_idx = paragraph_indexes[ideal_paragraph_pos]
			image_positions.append(image_block_idx)

	if for_image:
		# 长图片专用样式
		html_parts = [
			"<!doctype html>",
			"<html lang='zh-CN'>",
			"<head>",
			"  <meta charset='UTF-8' />",
			"  <meta name='viewport' content='width=device-width, initial-scale=1.0' />",
			f"  <title>{title}</title>",
			"  <style>",
			"    * { margin: 0; padding: 0; box-sizing: border-box; }",
			"    body { font-family: 'PingFang SC','Microsoft YaHei',sans-serif; color: #1f2937; background: linear-gradient(180deg, #fffaf0 0%, #fffdf8 100%); line-height: 1.9; min-height: 100vh; }",
			"    .container { width: 750px; margin: 0 auto; padding: 40px 30px; background: #fff; box-shadow: 0 0 40px rgba(0,0,0,0.08); }",
			"    .header { text-align: center; margin-bottom: 36px; padding-bottom: 24px; border-bottom: 3px solid #ff9f45; }",
			"    h1 { font-size: 42px; font-weight: 800; color: #111827; letter-spacing: 2px; line-height: 1.4; }",
			"    h2 { font-size: 28px; margin: 36px 0 18px; color: #111827; border-left: 6px solid #ff9f45; padding-left: 16px; font-weight: 700; background: linear-gradient(90deg, #fff7ed 0%, transparent 100%); padding-top: 8px; padding-bottom: 8px; border-radius: 0 8px 8px 0; }",
			"    p { font-size: 20px; margin: 16px 0; text-indent: 2em; color: #374151; line-height: 2; }",
			"    figure { margin: 24px 0 28px; }",
			"    img { display: block; width: 100%; height: auto; border-radius: 16px; border: 2px solid #f3f4f6; box-shadow: 0 8px 24px rgba(0,0,0,0.08); }",
			"    figcaption { margin-top: 12px; font-size: 16px; line-height: 1.6; color: #6b7280; text-align: center; padding: 0 20px; }",
			"    .glossary { margin-top: 40px; background: linear-gradient(135deg, #fff7ed 0%, #ffedd5 100%); border: 2px solid #fed7aa; border-radius: 16px; padding: 24px 28px; }",
			"    .glossary h3 { margin: 0 0 18px; font-size: 24px; color: #9a3412; font-weight: 700; display: flex; align-items: center; }",
			"    .glossary h3::before { content: '📚'; margin-right: 10px; }",
			"    .term { margin: 14px 0; font-size: 18px; padding: 12px 16px; background: #fff; border-radius: 10px; border-left: 4px solid #f59e0b; }",
			"    .term strong { color: #92400e; font-size: 20px; }",
			"    .highlight-term { background: linear-gradient(120deg, #fef3c7 0%, #fde68a 100%); padding: 4px 10px; border-radius: 6px; font-weight: 700; color: #92400e; border-bottom: 3px solid #f59e0b; }",
			"    .footer { margin-top: 48px; padding-top: 24px; border-top: 1px solid #e5e7eb; text-align: center; color: #9ca3af; font-size: 14px; }",
			"  </style>",
			"</head>",
			"<body>",
			"  <div class='container'>",
			"    <div class='header'>",
			f"      <h1>{title}</h1>",
			"    </div>",
		]
	else:
		# PDF 专用样式
		html_parts = [
			"<!doctype html>",
			"<html lang='zh-CN'>",
			"<head>",
			"  <meta charset='UTF-8' />",
			"  <meta name='viewport' content='width=device-width, initial-scale=1.0' />",
			f"  <title>{title}</title>",
			"  <style>",
			"    @page { size: A4; margin: 16mm 14mm; }",
			"    body { font-family: 'PingFang SC','Microsoft YaHei',sans-serif; color: #1f2937; background: #fffdf8; line-height: 1.85; }",
			"    .page { max-width: 900px; margin: 0 auto; padding: 24px; }",
			"    h1 { text-align: center; font-size: 30px; margin: 8px 0 24px; color: #111827; }",
			"    h2 { font-size: 23px; margin: 22px 0 12px; color: #111827; border-left: 5px solid #ff9f45; padding-left: 10px; }",
			"    p { font-size: 16px; margin: 10px 0; text-indent: 2em; orphans: 3; widows: 3; }",
			"    figure { margin: 8px 0 12px; break-inside: avoid-page; page-break-inside: avoid; }",
			"    img { display: block; width: 100%; height: auto; max-height: 58vh; object-fit: contain; border-radius: 14px; border: 1px solid #e5e7eb; }",
			"    figcaption { margin-top: 6px; font-size: 12px; line-height: 1.4; color: #6b7280; text-align: center; }",
			"    .glossary { margin-top: 28px; background: #fff7ed; border: 1px solid #fed7aa; border-radius: 14px; padding: 16px; }",
			"    .glossary h3 { margin: 0 0 10px; font-size: 18px; color: #9a3412; }",
			"    .term { margin: 8px 0; font-size: 15px; }",
			"    .highlight-term { background: linear-gradient(120deg, #fef3c7 0%, #fde68a 100%); padding: 2px 6px; border-radius: 4px; font-weight: 600; color: #92400e; border-bottom: 2px solid #f59e0b; }",
			"  </style>",
			"</head>",
			"<body>",
			"  <div class='page'>",
			f"    <h1>{title}</h1>",
		]

	for block_idx, block in enumerate(blocks):
		if block["type"] == "heading":
			indent = "    " if not for_image else "    "
			html_parts.append(f"{indent}<h2>{block['text']}</h2>")
			continue

		indent = "    " if not for_image else "    "
		html_parts.append(f"{indent}<p>{block['text']}</p>")

		# 检查当前段落后面是否需要放图片
		# 找出所有在当前位置的图片
		images_for_this_block = []
		for img_idx, pos in enumerate(image_positions):
			if pos == block_idx:
				images_for_this_block.append(img_idx)

		# 插入图片
		img_indent = "    " if not for_image else "    "
		for img_idx in images_for_this_block:
			if img_idx < len(illustrations):
				image = illustrations[img_idx] or {}
				image_url = image.get("image_url", "")
				caption = image.get("summary") or image.get("image_prompt") or f"配图 {img_idx + 1}"
				if image_url:
					html_parts.append(f"{img_indent}<figure>")
					html_parts.append(f"{img_indent}  <img src='{image_url}' alt='story-image-{img_idx + 1}' />")
					html_parts.append(f"{img_indent}  <figcaption>{caption}</figcaption>")
					html_parts.append(f"{img_indent}</figure>")

	if render_glossary:
		sec_indent = "    " if not for_image else "    "
		html_parts.append(f"{sec_indent}<section class='glossary'>")
		html_parts.append(f"{sec_indent}  <h3>科学词条小卡片</h3>")
		for item in render_glossary:
			term = item.get("term", "")
			explanation = item.get("explanation", "")
			html_parts.append(f"{sec_indent}  <p class='term'><strong>{term}</strong>：{explanation}</p>")
		html_parts.append(f"{sec_indent}</section>")

	if for_image:
		html_parts.extend([
			"    <div class='footer'>",
			"      <p>✨ 由童科绘生成 ✨</p>",
			"    </div>",
			"  </div>",
			"</body>",
			"</html>",
		])
	else:
		html_parts.extend([
			"  </div>",
			"</body>",
			"</html>",
		])

	return "\n".join(html_parts)


def _html_to_long_image(html_content: str, output_path: str) -> str:
	"""
	使用 Playwright 将 HTML 转换为长图片
	通过独立的 Python 脚本运行，避免同步 API 问题
	"""
	import os
	import tempfile
	import subprocess
	import sys

	# 利用一个临时文件存放HTML
	with tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode="w", encoding="utf-8") as tmp_file:
		tmp_file.write(html_content)
		tmp_html_path = tmp_file.name

	try:
		# 创建一个独立的 Python 脚本来运行 Playwright
		script_content = f'''
import asyncio
import sys
from playwright.async_api import async_playwright

async def main():
    html_path = r"{tmp_html_path}"
    output_path = r"{output_path}"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={{"width": 750, "height": 2000}})
        await page.goto(f"file:///{{html_path.replace(os.sep, '/')}}", wait_until="networkidle")
        await page.screenshot(path=output_path, full_page=True, scale="device")
        await browser.close()

if __name__ == "__main__":
    import os
    asyncio.run(main())
'''

		with tempfile.NamedTemporaryFile(delete=False, suffix=".py", mode="w", encoding="utf-8") as script_file:
			script_file.write(script_content)
			script_path = script_file.name

		try:
			# 运行独立脚本
			result = subprocess.run(
				[sys.executable, script_path],
				capture_output=True,
				text=True,
				timeout=120,
			)

			if result.returncode != 0:
				# 如果失败，尝试检查并安装 Playwright
				error_msg = result.stderr or result.stdout or ""
				if any(keyword in error_msg.lower() for keyword in ["executable doesn't exist", "browser has been closed", "playwright"]):
					# 安装 Playwright Chromium
					subprocess.run(
						[sys.executable, "-m", "playwright", "install", "chromium"],
						capture_output=True,
						timeout=300,
					)
					# 重试
					result = subprocess.run(
						[sys.executable, script_path],
						capture_output=True,
						text=True,
						timeout=120,
					)
					if result.returncode != 0:
						raise RuntimeError(f"Playwright 执行失败: {result.stderr or result.stdout}")
				else:
					raise RuntimeError(f"图片生成失败: {error_msg}")

			# 验证输出文件
			if not os.path.exists(output_path) or os.path.getsize(output_path) < 1024:
				raise RuntimeError("生成的图片文件异常或过小")

			return output_path

		finally:
			# 清理临时脚本文件
			if os.path.exists(script_path):
				os.remove(script_path)

	finally:
		# 清理临时HTML文件
		if os.path.exists(tmp_html_path):
			os.remove(tmp_html_path)


@router.post("/export-pdf", summary="导出排版后的 PDF")
def export_pdf(req: schemas.PublisherRequest):
	title = (req.title or "未命名文章").strip()
	content = (req.content or "").strip()
	glossary = req.glossary or []
	illustrations = req.illustrations or []
	highlight_terms = req.highlight_terms or []

	if not content:
		return error(code=400, msg="正文为空，无法导出 PDF")

	html_content = _build_layout_html(title, content, glossary, illustrations, highlight_terms)
	filename = f"{_safe_name(title)}-{int(time.time())}.pdf"
	output_path = ARTICLE_DIR / filename

	try:
		PDFGenerator.html_to_pdf(html_content, str(output_path))
	except Exception as exc:
		detail = str(exc).strip() or exc.__class__.__name__
		hint = (
			"请检查服务器 PDF 依赖："
			"1) pip install weasyprint；"
			"2) 若使用 Playwright 降级，请执行 python -m playwright install chromium。"
		)
		return error(code=500, msg=f"PDF 生成失败: {detail}。{hint}")

	return success(
		{
			"filename": filename,
			"download_url": f"/api/publisher/download/{filename}",
		},
		msg="PDF 导出成功",
	)


@router.get("/download/{filename}", summary="查看或下载已导出的 PDF")
def download_pdf(filename: str):
	file_path = (ARTICLE_DIR / filename).resolve()
	article_root = ARTICLE_DIR.resolve()

	if article_root not in file_path.parents:
		return error(code=400, msg="非法文件路径")
	if not file_path.exists() or not file_path.is_file():
		return error(code=404, msg="文件不存在")

	# 根据扩展名设置正确的 media_type
	if file_path.suffix.lower() == ".pdf":
		media_type = "application/pdf"
	elif file_path.suffix.lower() in (".png", ".jpg", ".jpeg"):
		media_type = "image/png" if file_path.suffix.lower() == ".png" else "image/jpeg"
	else:
		media_type = "application/octet-stream"

	return FileResponse(
		path=str(file_path),
		media_type=media_type,
		filename=file_path.name,
	)


@router.post("/export-image", summary="导出排版后的长图片")
def export_image(req: schemas.PublisherRequest):
	title = (req.title or "未命名文章").strip()
	content = (req.content or "").strip()
	glossary = req.glossary or []
	illustrations = req.illustrations or []
	highlight_terms = req.highlight_terms or []

	if not content:
		return error(code=400, msg="正文为空，无法导出图片")

	html_content = _build_layout_html(title, content, glossary, illustrations, highlight_terms, for_image=True)
	filename = f"{_safe_name(title)}-{int(time.time())}.png"
	output_path = ARTICLE_DIR / filename

	try:
		_html_to_long_image(html_content, str(output_path))
	except Exception as exc:
		detail = str(exc).strip() or exc.__class__.__name__
		hint = (
			"请检查服务器图片生成依赖："
			"执行 python -m playwright install chromium。"
		)
		return error(code=500, msg=f"长图片生成失败: {detail}。{hint}")

	return success(
		{
			"filename": filename,
			"download_url": f"/api/publisher/download/{filename}",
		},
		msg="长图片导出成功",
	)
