"""
维基百科 API 客户端
用于科学审查者RAG知识库接入
支持中文维基百科搜索和内容获取
"""
import requests
from typing import Dict, Any, List, Optional
import re
import html

# 中文维基百科API端点
WIKIPEDIA_API_URL = "https://zh.wikipedia.org/w/api.php"
WIKIPEDIA_PAGE_URL = "https://zh.wikipedia.org/wiki/"

# 用户代理（维基百科要求提供有效的User-Agent）
USER_AGENT = "TongKeHui/1.0 (https://github.com/your-org/tongkehui; your-email@example.com)"


def _clean_html(text: str) -> str:
    """清理HTML标签，转换HTML实体"""
    # 移除HTML标签
    clean = re.sub(r"<[^>]+>", "", text)
    # 转换HTML实体
    clean = html.unescape(clean)
    # 清理多余空白
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def search_wikipedia(
    query: str,
    limit: int = 5,
    language: str = "zh"
) -> List[Dict[str, Any]]:
    """
    搜索维基百科页面

    :param query: 搜索关键词
    :param limit: 返回结果数量
    :param language: 语言代码（zh=中文，en=英文）
    :return: 搜索结果列表，包含title、pageid、snippet等
    """
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srlimit": limit,
        "srprop": "snippet|titlesnippet",
        "format": "json",
        "utf8": 1,
    }

    # 切换语言
    api_url = WIKIPEDIA_API_URL
    if language != "zh":
        api_url = f"https://{language}.wikipedia.org/w/api.php"

    try:
        response = requests.get(
            api_url,
            params=params,
            headers={"User-Agent": USER_AGENT},
            timeout=15
        )
        response.raise_for_status()
        data = response.json()

        results = []
        for item in data.get("query", {}).get("search", []):
            results.append({
                "pageid": item.get("pageid"),
                "title": item.get("title", ""),
                "snippet": _clean_html(item.get("snippet", "")),
                "url": f"{WIKIPEDIA_PAGE_URL}{item.get('title', '').replace(' ', '_')}" if item.get("title") else None,
            })
        return results
    except Exception as e:
        print(f"维基百科搜索失败: {str(e)}")
        return []


def get_wikipedia_page_content(
    pageid: Optional[int] = None,
    title: Optional[str] = None,
    language: str = "zh"
) -> Optional[Dict[str, Any]]:
    """
    获取维基百科页面完整内容

    :param pageid: 页面ID（与title二选一）
    :param title: 页面标题（与pageid二选一）
    :param language: 语言代码
    :return: 页面内容字典，包含title、content、categories等
    """
    if not pageid and not title:
        return None

    params = {
        "action": "query",
        "prop": "extracts|categories|info",
        "explaintext": 1,  # 返回纯文本而非HTML
        "exsectionformat": "wiki",
        "inprop": "url",
        "format": "json",
        "utf8": 1,
    }

    if pageid:
        params["pageids"] = str(pageid)
    elif title:
        params["titles"] = title

    # 切换语言
    api_url = WIKIPEDIA_API_URL
    if language != "zh":
        api_url = f"https://{language}.wikipedia.org/w/api.php"

    try:
        response = requests.get(
            api_url,
            params=params,
            headers={"User-Agent": USER_AGENT},
            timeout=20
        )
        response.raise_for_status()
        data = response.json()

        pages = data.get("query", {}).get("pages", {})
        if not pages:
            return None

        # 获取第一个页面
        page_id = next(iter(pages.keys()))
        page = pages.get(page_id, {})

        if "missing" in page:
            return None

        # 提取分类
        categories = []
        for cat in page.get("categories", []):
            cat_title = cat.get("title", "")
            if cat_title.startswith("Category:"):
                categories.append(cat_title[len("Category:"):])

        return {
            "pageid": page.get("pageid"),
            "title": page.get("title", ""),
            "content": page.get("extract", ""),
            "categories": categories,
            "url": page.get("fullurl", ""),
            "language": language,
        }
    except Exception as e:
        print(f"获取维基百科页面失败: {str(e)}")
        return None


def search_and_ingest_wikipedia(
    db,
    query: str,
    doc_type: str = "SCIENCE_FACT",
    authority_level: int = 90,
    limit: int = 3,
    language: str = "zh",
    publisher: str = "维基百科"
) -> List[Dict[str, Any]]:
    """
    搜索维基百科并自动入库到RAG知识库

    :param db: 数据库会话
    :param query: 搜索关键词
    :param doc_type: 文档类型（默认SCIENCE_FACT用于科学审查者）
    :param authority_level: 权威级别（默认90）
    :param limit: 入库数量
    :param language: 语言
    :param publisher: 发布者名称
    :return: 入库结果列表
    """
    from utils.fact_rag import index_fact_document

    # 1. 搜索维基百科
    search_results = search_wikipedia(query, limit=limit, language=language)
    if not search_results:
        return []

    ingested = []

    # 2. 获取每个页面的完整内容并入库
    for item in search_results:
        page_content = get_wikipedia_page_content(
            pageid=item.get("pageid"),
            language=language
        )

        if not page_content or not page_content.get("content"):
            continue

        # 构建入库payload
        topic_tags = page_content.get("categories", [])[:8]  # 最多8个分类作为标签

        try:
            result = index_fact_document(
                db,
                {
                    "source_name": f"维基百科: {page_content.get('title', '')}",
                    "source_url": page_content.get("url"),
                    "publisher": publisher,
                    "authority_level": authority_level,
                    "doc_type": doc_type,
                    "topic_tags": topic_tags,
                    "audience_tags": ["科普", "科学知识"],
                    "content": page_content.get("content", ""),
                }
            )
            result["wikipedia_title"] = page_content.get("title")
            result["wikipedia_url"] = page_content.get("url")
            ingested.append(result)
        except Exception as e:
            print(f"入库维基百科页面失败 {page_content.get('title')}: {str(e)}")
            continue

    return ingested
