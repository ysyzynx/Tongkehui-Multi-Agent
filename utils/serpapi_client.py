"""
SerpAPI 谷歌学术 API 客户端
用于科学审查者RAG知识库接入
注意：由于免费额度有限，默认保持关闭
"""
import requests
from typing import Dict, Any, List, Optional
from config.settings import settings

# SerpAPI 端点
SERPAPI_URL = "https://serpapi.com/search"


def search_google_scholar(
    query: str,
    api_key: str = None,
    limit: int = 5,
    language: str = "zh-CN"
) -> List[Dict[str, Any]]:
    """
    使用 SerpAPI 搜索谷歌学术

    :param query: 搜索关键词
    :param api_key: SerpAPI API Key（如果不传则从 settings 读取）
    :param limit: 返回结果数量
    :param language: 语言参数
    :return: 搜索结果列表
    """
    if not api_key:
        api_key = getattr(settings, "SERPAPI_API_KEY", None)

    if not api_key:
        print("SerpAPI API Key 未配置")
        return []

    params = {
        "engine": "google_scholar",
        "q": query,
        "api_key": api_key,
        "hl": language,
        "num": min(limit, 20),  # SerpAPI 最多一次返回 20 条
    }

    try:
        response = requests.get(SERPAPI_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        results = []
        organic_results = data.get("organic_results", [])

        for item in organic_results:
            # 提取摘要
            snippet = item.get("snippet", "")
            # 尝试获取更多内容
            if not snippet:
                snippet = item.get("publication_summary", "")
            if not snippet:
                snippet = item.get("summary", "")

            # 构建结果
            result = {
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": snippet,
                "authors": _extract_authors(item),
                "publication_info": item.get("publication_info", {}),
                "cited_by": item.get("inline_links", {}).get("cited_by", {}).get("total", 0),
                "type": "google_scholar",
            }
            results.append(result)

        return results[:limit]
    except Exception as e:
        print(f"谷歌学术搜索失败: {str(e)}")
        return []


def _extract_authors(item: Dict[str, Any]) -> str:
    """从结果中提取作者信息"""
    try:
        pub_info = item.get("publication_info", {})
        if pub_info:
            summary = pub_info.get("summary", "")
            if summary and " - " in summary:
                return summary.split(" - ")[0].strip()
        return ""
    except Exception:
        return ""


def search_and_ingest_google_scholar(
    db,
    query: str,
    doc_type: str = "SCIENCE_FACT",
    authority_level: int = 95,
    limit: int = 3,
    api_key: str = None,
    publisher: str = "谷歌学术",
    language: str = "zh-CN"
) -> List[Dict[str, Any]]:
    """
    搜索谷歌学术并自动入库到RAG知识库

    :param db: 数据库会话
    :param query: 搜索关键词
    :param doc_type: 文档类型
    :param authority_level: 权威级别（谷歌学术默认95）
    :param limit: 入库数量
    :param api_key: SerpAPI Key
    :param publisher: 发布者名称
    :param language: 语言
    :return: 入库结果列表
    """
    from utils.fact_rag import index_fact_document

    # 1. 搜索谷歌学术
    search_results = search_google_scholar(
        query=query,
        api_key=api_key,
        limit=limit,
        language=language
    )
    if not search_results:
        return []

    ingested = []

    # 2. 逐个入库
    for item in search_results:
        title = item.get("title", "")
        snippet = item.get("snippet", "")

        if not title or not snippet:
            continue

        # 构建内容：标题 + 摘要
        content_parts = [f"标题：{title}"]
        authors = item.get("authors", "")
        if authors:
            content_parts.append(f"作者：{authors}")
        cited_by = item.get("cited_by", 0)
        if cited_by:
            content_parts.append(f"引用次数：{cited_by}")
        content_parts.append(f"\n摘要：{snippet}")

        content = "\n".join(content_parts)

        # 构建话题标签
        topic_tags = []
        # 从标题中提取一些关键词作为标签
        title_words = [w for w in title.split() if len(w) >= 2]
        topic_tags.extend(title_words[:5])

        try:
            result = index_fact_document(
                db,
                {
                    "source_name": f"谷歌学术: {title}",
                    "source_url": item.get("link"),
                    "publisher": publisher,
                    "authority_level": authority_level,
                    "doc_type": doc_type,
                    "topic_tags": topic_tags,
                    "audience_tags": ["学术文献", "科学研究"],
                    "content": content,
                }
            )
            result["scholar_title"] = title
            result["scholar_url"] = item.get("link")
            result["cited_by"] = item.get("cited_by", 0)
            ingested.append(result)
        except Exception as e:
            print(f"入库谷歌学术文献失败 {title}: {str(e)}")
            continue

    return ingested
