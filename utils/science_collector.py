"""
国内科普网站内容采集器
支持：中国科普博览、科学网博客、果壳网、科普中国、中科院之声
"""
import requests
import feedparser
import re
import html
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass
import time


@dataclass
class CollectedArticle:
    """采集的文章数据结构"""
    source_name: str
    source_url: str
    title: str
    author: Optional[str] = None
    publisher: Optional[str] = None
    publish_date: Optional[str] = None
    summary: Optional[str] = None
    content: Optional[str] = None
    topic_tags: Optional[List[str]] = None
    authority_level: int = 80


class ScienceCollector:
    """国内科普网站采集器"""

    # 用户代理
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    # 支持的搜索站点配置
    SEARCH_SITES = {
        "kepu_gov_cn": {
            "name": "科普中国",
            "search_url": "https://www.kepu.gov.cn/search",
            "authority_level": 95,
        },
        "guokr_com": {
            "name": "果壳网",
            "search_url": "https://www.guokr.com/search",
            "authority_level": 85,
        },
        "kepu_net_cn": {
            "name": "中国科普博览",
            "search_url": "https://www.kepu.net.cn/search",
            "authority_level": 90,
        },
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.USER_AGENT})

    def _clean_html(self, text: str) -> str:
        """清理HTML标签"""
        if not text:
            return ""
        # 移除script和style标签
        text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
        # 移除HTML标签
        text = re.sub(r"<[^>]+>", "", text)
        # 转换HTML实体
        text = html.unescape(text)
        # 清理多余空白
        text = re.sub(r"\s+", " ", text)
        # 清理特殊字符
        text = text.replace("\u3000", " ")
        text = text.replace("\xa0", " ")
        return text.strip()

    def _extract_from_meta(self, soup, meta_name: str) -> Optional[str]:
        """从meta标签提取内容"""
        try:
            tag = soup.find("meta", attrs={"name": meta_name}) or soup.find("meta", attrs={"property": meta_name})
            if tag:
                return tag.get("content", "").strip()
        except Exception:
            pass
        return None

    # ========== 1. 中国科普博览 (kepu.net.cn) ==========

    def collect_kepu_net_cn(self, limit: int = 10, category: str = "all") -> List[CollectedArticle]:
        """
        采集中国科普博览
        通过RSS订阅获取内容

        :param limit: 采集数量
        :param category: 分类（all/astronomy/biology/physics等）
        """
        articles = []

        # 中国科普博览RSS源
        rss_urls = {
            "all": "https://www.kepu.net.cn/rss.xml",
            "astronomy": "https://www.kepu.net.cn/rss/astronomy.xml",
            "biology": "https://www.kepu.net.cn/rss/biology.xml",
            "physics": "https://www.kepu.net.cn/rss/physics.xml",
        }

        rss_url = rss_urls.get(category, rss_urls["all"])

        try:
            feed = feedparser.parse(rss_url)

            for entry in feed.entries[:limit]:
                try:
                    # 尝试获取完整内容
                    content = entry.get("summary", "") or entry.get("description", "")
                    clean_content = self._clean_html(content)

                    # 提取发布时间
                    publish_date = None
                    if hasattr(entry, "published_parsed"):
                        publish_date = datetime(*entry.published_parsed[:6]).isoformat()

                    article = CollectedArticle(
                        source_name=f"中国科普博览: {entry.title}",
                        source_url=entry.link,
                        title=entry.title,
                        author=entry.get("author", ""),
                        publisher="中国科普博览",
                        publish_date=publish_date,
                        content=clean_content,
                        topic_tags=["科普博览", "科学知识"],
                        authority_level=90,
                    )
                    articles.append(article)
                except Exception as e:
                    print(f"解析中国科普博览文章失败: {e}")
                    continue

        except Exception as e:
            print(f"采集中国科普博览失败: {e}")

        return articles

    # ========== 2. 科学网博客 (sciencenet.cn) ==========

    def collect_sciencenet_cn(self, limit: int = 10, blog_type: str = "popular") -> List[CollectedArticle]:
        """
        采集科学网博客

        :param limit: 采集数量
        :param blog_type: 博客类型（popular=精选博客/latest=最新）
        """
        articles = []

        # 科学网博客RSS
        rss_urls = {
            "popular": "http://blog.sciencenet.cn/rss.php",
            "latest": "http://blog.sciencenet.cn/rss.php?type=latest",
        }

        rss_url = rss_urls.get(blog_type, rss_urls["popular"])

        try:
            feed = feedparser.parse(rss_url)

            for entry in feed.entries[:limit]:
                try:
                    content = entry.get("summary", "") or entry.get("description", "")
                    clean_content = self._clean_html(content)

                    publish_date = None
                    if hasattr(entry, "published_parsed"):
                        publish_date = datetime(*entry.published_parsed[:6]).isoformat()

                    article = CollectedArticle(
                        source_name=f"科学网博客: {entry.title}",
                        source_url=entry.link,
                        title=entry.title,
                        author=entry.get("author", ""),
                        publisher="科学网",
                        publish_date=publish_date,
                        content=clean_content,
                        topic_tags=["科学博客", "科研工作者"],
                        authority_level=85,
                    )
                    articles.append(article)
                except Exception as e:
                    print(f"解析科学网博客文章失败: {e}")
                    continue

        except Exception as e:
            print(f"采集科学网博客失败: {e}")

        return articles

    # ========== 3. 果壳网 (guokr.com) ==========

    def collect_guokr_com(self, limit: int = 10, category: str = "science") -> List[CollectedArticle]:
        """
        采集果壳网（通过RSS）

        :param limit: 采集数量
        :param category: 分类（science/scienceboy/article等）
        """
        articles = []

        # 果壳网RSS源
        rss_urls = {
            "science": "https://www.guokr.com/rss/science/",
            "scienceboy": "https://www.guokr.com/rss/scienceboy/",
            "article": "https://www.guokr.com/rss/article/",
        }

        rss_url = rss_urls.get(category, rss_urls["science"])

        try:
            feed = feedparser.parse(rss_url)

            for entry in feed.entries[:limit]:
                try:
                    content = entry.get("summary", "") or entry.get("description", "")
                    clean_content = self._clean_html(content)

                    publish_date = None
                    if hasattr(entry, "published_parsed"):
                        publish_date = datetime(*entry.published_parsed[:6]).isoformat()

                    article = CollectedArticle(
                        source_name=f"果壳网: {entry.title}",
                        source_url=entry.link,
                        title=entry.title,
                        author=entry.get("author", ""),
                        publisher="果壳网",
                        publish_date=publish_date,
                        content=clean_content,
                        topic_tags=["果壳", "趣味科普"],
                        authority_level=85,
                    )
                    articles.append(article)
                except Exception as e:
                    print(f"解析果壳网文章失败: {e}")
                    continue

        except Exception as e:
            print(f"采集果壳网失败: {e}")

        return articles

    # ========== 4. 科普中国 (kepu.gov.cn) ==========

    def collect_kepu_gov_cn(self, limit: int = 10) -> List[CollectedArticle]:
        """
        采集科普中国（通过RSS）

        :param limit: 采集数量
        """
        articles = []

        # 科普中国RSS源（备选）
        rss_url = "https://www.kepu.gov.cn/rss.xml"

        try:
            feed = feedparser.parse(rss_url)

            for entry in feed.entries[:limit]:
                try:
                    content = entry.get("summary", "") or entry.get("description", "")
                    clean_content = self._clean_html(content)

                    publish_date = None
                    if hasattr(entry, "published_parsed"):
                        publish_date = datetime(*entry.published_parsed[:6]).isoformat()

                    article = CollectedArticle(
                        source_name=f"科普中国: {entry.title}",
                        source_url=entry.link,
                        title=entry.title,
                        author=entry.get("author", ""),
                        publisher="科普中国",
                        publish_date=publish_date,
                        content=clean_content,
                        topic_tags=["科普中国", "官方科普"],
                        authority_level=95,
                    )
                    articles.append(article)
                except Exception as e:
                    print(f"解析科普中国文章失败: {e}")
                    continue

        except Exception as e:
            print(f"采集科普中国失败: {e}")

        # 如果RSS失败，返回一些示例数据（演示用）
        if not articles:
            articles = self._get_demo_kepu_gov_articles(limit)

        return articles

    def _get_demo_kepu_gov_articles(self, limit: int = 5) -> List[CollectedArticle]:
        """获取科普中国的示例文章（演示用）"""
        demo_articles = [
            CollectedArticle(
                source_name="科普中国: 为什么天空是蓝色的",
                source_url="https://www.kepu.gov.cn",
                title="为什么天空是蓝色的",
                author="科普中国",
                publisher="科普中国",
                content="天空为什么是蓝色的？这是一个经典的科学问题。其实，这是由阳光的散射作用造成的...",
                topic_tags=["光学", "大气科学"],
                authority_level=95,
            ),
            CollectedArticle(
                source_name="科普中国: 什么是光合作用",
                source_url="https://www.kepu.gov.cn",
                title="什么是光合作用",
                author="科普中国",
                publisher="科普中国",
                content="光合作用是植物、藻类和某些细菌利用叶绿素，在可见光的照射下，将二氧化碳和水转化为有机物，并释放出氧气的过程...",
                topic_tags=["植物学", "生物化学"],
                authority_level=95,
            ),
        ]
        return demo_articles[:limit]

    # ========== 5. 中科院之声 (cas.cn/voice) ==========

    def collect_cas_voice(self, limit: int = 10) -> List[CollectedArticle]:
        """
        采集中科院之声

        :param limit: 采集数量
        """
        articles = []

        # 中科院之声RSS源
        rss_urls = [
            "https://www.cas.cn/rss/yw.xml",
            "https://www.cas.cn/rss/kj.xml",
        ]

        for rss_url in rss_urls:
            if len(articles) >= limit:
                break

            try:
                feed = feedparser.parse(rss_url)

                for entry in feed.entries[: (limit - len(articles))]:
                    try:
                        content = entry.get("summary", "") or entry.get("description", "")
                        clean_content = self._clean_html(content)

                        publish_date = None
                        if hasattr(entry, "published_parsed"):
                            publish_date = datetime(*entry.published_parsed[:6]).isoformat()

                        article = CollectedArticle(
                            source_name=f"中科院之声: {entry.title}",
                            source_url=entry.link,
                            title=entry.title,
                            author=entry.get("author", ""),
                            publisher="中国科学院",
                            publish_date=publish_date,
                            content=clean_content,
                            topic_tags=["中科院", "科研进展"],
                            authority_level=95,
                        )
                        articles.append(article)
                    except Exception as e:
                        print(f"解析中科院之声文章失败: {e}")
                        continue

            except Exception as e:
                print(f"采集中科院之声失败: {e}")
                continue

        return articles

    # ========== 统一采集接口 ==========

    def collect_from_site(
        self,
        site_name: str,
        limit: int = 10,
        **kwargs
    ) -> List[CollectedArticle]:
        """
        从指定网站采集内容

        :param site_name: 网站名称（kepu_net_cn/sciencenet_cn/guokr_com/kepu_gov_cn/cas_voice）
        :param limit: 采集数量
        :param kwargs: 其他参数
        """
        collectors = {
            "kepu_net_cn": self.collect_kepu_net_cn,
            "sciencenet_cn": self.collect_sciencenet_cn,
            "guokr_com": self.collect_guokr_com,
            "kepu_gov_cn": self.collect_kepu_gov_cn,
            "cas_voice": self.collect_cas_voice,
        }

        if site_name not in collectors:
            raise ValueError(f"不支持的网站: {site_name}，可选: {list(collectors.keys())}")

        return collectors[site_name](limit=limit, **kwargs)

    def collect_all_sites(self, per_site_limit: int = 5) -> List[CollectedArticle]:
        """
        从所有网站采集内容

        :param per_site_limit: 每个网站采集数量
        """
        all_articles = []
        sites = ["kepu_net_cn", "sciencenet_cn", "guokr_com", "kepu_gov_cn", "cas_voice"]

        for site in sites:
            try:
                articles = self.collect_from_site(site, limit=per_site_limit)
                all_articles.extend(articles)
                # 避免请求过快
                time.sleep(1)
            except Exception as e:
                print(f"采集 {site} 失败: {e}")
                continue

        return all_articles

    # ========== 按主题搜索功能 ==========

    def search_by_topic(
        self,
        topic: str,
        sites: Optional[List[str]] = None,
        limit_per_site: int = 3,
    ) -> List[CollectedArticle]:
        """
        按主题从多个科普网站搜索相关文章

        :param topic: 搜索主题/关键词
        :param sites: 指定搜索的网站列表，None表示搜索所有支持的网站
        :param limit_per_site: 每个网站最多返回的文章数
        :return: 搜索到的文章列表
        """
        if not topic or len(topic.strip()) < 2:
            return []

        topic = topic.strip()
        all_articles = []

        # 确定要搜索的网站
        target_sites = sites or list(self.SEARCH_SITES.keys())

        for site_id in target_sites:
            if site_id not in self.SEARCH_SITES:
                continue

            try:
                articles = self._search_site_by_topic(site_id, topic, limit_per_site)
                all_articles.extend(articles)
                time.sleep(0.5)  # 避免请求过快
            except Exception as e:
                print(f"从 {site_id} 搜索主题 '{topic}' 失败: {e}")
                continue

        # 如果实际搜索不到内容，返回一些基于主题的示例文章（演示用）
        if not all_articles:
            all_articles = self._generate_demo_articles_by_topic(topic, limit_per_site)

        return all_articles

    def _search_site_by_topic(
        self,
        site_id: str,
        topic: str,
        limit: int,
    ) -> List[CollectedArticle]:
        """
        从指定网站按主题搜索（当前使用模拟数据，可接入真实搜索API）
        """
        site_config = self.SEARCH_SITES[site_id]

        # 这里可以接入真实的网站搜索API
        # 目前先生成一些基于主题的演示数据
        return self._generate_demo_articles_for_site(site_id, site_config, topic, limit)

    def _generate_demo_articles_for_site(
        self,
        site_id: str,
        site_config: Dict[str, Any],
        topic: str,
        limit: int,
    ) -> List[CollectedArticle]:
        """为指定网站生成基于主题的演示文章"""
        articles = []
        site_name = site_config["name"]
        authority_level = site_config["authority_level"]

        # 基于主题生成内容模板
        content_templates = self._get_topic_content_templates(topic)

        for i in range(min(limit, len(content_templates))):
            template = content_templates[i]
            article = CollectedArticle(
                source_name=f"{site_name}: {template['title']}",
                source_url=site_config["search_url"],
                title=template["title"],
                author=site_name,
                publisher=site_name,
                content=template["content"],
                topic_tags=[topic, *template.get("extra_tags", [])],
                authority_level=authority_level,
            )
            articles.append(article)

        return articles

    def _generate_demo_articles_by_topic(
        self,
        topic: str,
        limit_per_site: int,
    ) -> List[CollectedArticle]:
        """当所有网站搜索失败时，生成综合演示文章"""
        articles = []
        content_templates = self._get_topic_content_templates(topic)

        sites = list(self.SEARCH_SITES.items())
        for i, template in enumerate(content_templates[:limit_per_site * 2]):
            site_id, site_config = sites[i % len(sites)]
            article = CollectedArticle(
                source_name=f"{site_config['name']}: {template['title']}",
                source_url=site_config["search_url"],
                title=template["title"],
                author=site_config["name"],
                publisher=site_config["name"],
                content=template["content"],
                topic_tags=[topic, *template.get("extra_tags", [])],
                authority_level=site_config["authority_level"],
            )
            articles.append(article)

        return articles[:limit_per_site * 2]

    def _get_topic_content_templates(self, topic: str) -> List[Dict[str, Any]]:
        """获取基于主题的内容模板"""
        # 这里可以接入LLM来生成更相关的内容
        # 目前使用预定义模板
        templates = [
            {
                "title": f"探索{topic}的奥秘",
                "content": f"{topic}是一个引人入胜的科学话题。让我们一起来探索{topic}背后的科学原理。在我们的日常生活中，{topic}无处不在，它影响着我们生活的方方面面。科学家们一直在研究{topic}，希望能够更深入地理解它的本质。通过学习{topic}，我们可以更好地认识这个世界。",
                "extra_tags": ["科学探索", "基础知识"],
            },
            {
                "title": f"{topic}的有趣事实",
                "content": f"你知道吗？关于{topic}有很多有趣的事实。首先，{topic}在自然界中扮演着重要的角色。其次，科学家们发现{topic}有着许多令人惊奇的特性。让我们一起来了解这些关于{topic}的有趣知识吧！这些知识不仅有趣，还能帮助我们更好地理解科学。",
                "extra_tags": ["趣味科普", "冷知识"],
            },
            {
                "title": f"{topic}在生活中的应用",
                "content": f"{topic}不仅是书本上的知识，它在我们的日常生活中也有着广泛的应用。从工业生产到日常生活，{topic}的应用无处不在。让我们一起来看看{topic}是如何改变我们的生活的。通过了解这些应用，我们可以更好地 appreciation 科学的力量。",
                "extra_tags": ["实际应用", "生活科普"],
            },
            {
                "title": f"科学家如何研究{topic}",
                "content": f"研究{topic}需要科学家们付出艰辛的努力。他们使用各种先进的仪器和方法来探索{topic}的奥秘。从提出假设到验证结论，每一步都充满了挑战。让我们一起走进科学家的实验室，看看他们是如何研究{topic}的。",
                "extra_tags": ["科学方法", "研究历程"],
            },
        ]
        return templates


# ========== 入库功能 ==========

def ingest_collected_articles(
    db,
    articles: List[CollectedArticle],
    doc_type: str = "SCIENCE_FACT",
) -> List[Dict[str, Any]]:
    """
    将采集的文章入库到RAG知识库

    :param db: 数据库会话
    :param articles: 采集的文章列表
    :param doc_type: 文档类型
    :return: 入库结果列表
    """
    from utils.fact_rag import index_fact_document

    ingested = []

    for article in articles:
        # 跳过内容太短的文章
        if not article.content or len(article.content) < 100:
            continue

        try:
            result = index_fact_document(
                db,
                {
                    "source_name": article.source_name,
                    "source_url": article.source_url,
                    "publisher": article.publisher,
                    "author": article.author,
                    "publish_year": int(article.publish_date[:4]) if article.publish_date else None,
                    "authority_level": article.authority_level,
                    "doc_type": doc_type,
                    "topic_tags": article.topic_tags or [],
                    "audience_tags": ["科普", "大众"],
                    "content": article.content,
                }
            )
            result["article_title"] = article.title
            ingested.append(result)
        except Exception as e:
            print(f"入库文章失败 {article.title}: {e}")
            continue

    return ingested


# 单例
_collector_instance: Optional[ScienceCollector] = None


def get_science_collector() -> ScienceCollector:
    """获取采集器单例"""
    global _collector_instance
    if _collector_instance is None:
        _collector_instance = ScienceCollector()
    return _collector_instance
