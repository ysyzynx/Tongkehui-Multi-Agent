import os
import subprocess
import sys
import tempfile

class PDFGenerator:
    """
    负责将最终的HTML文本通过 WeasyPrint 渲染为高质量的PDF文件。
    优先使用 WeasyPrint，Playwright 作为备选方案。
    """

    @staticmethod
    def _render_by_weasyprint(html_content: str, output_abs_path: str) -> str:
        from weasyprint import HTML

        HTML(string=html_content, base_url=os.getcwd()).write_pdf(output_abs_path)
        return output_abs_path

    @staticmethod
    def _ensure_playwright_chromium() -> None:
        """在服务端缺少 Playwright 浏览器内核时尝试自动安装。"""
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    @staticmethod
    def _render_by_playwright(html_content: str, output_abs_path: str) -> str:
        # 利用一个临时文件存放HTML，供Playwright读取
        with tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode="w", encoding="utf-8") as tmp_file:
            tmp_file.write(html_content)
            tmp_url = f"file:///{tmp_file.name.replace(os.sep, '/')}"

        try:
            from playwright.sync_api import sync_playwright

            def _do_render() -> str:
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    page = browser.new_page()
                    page.goto(tmp_url, wait_until="networkidle")
                    page.pdf(
                        path=output_abs_path,
                        format="A4",
                        print_background=True,
                        margin={"top": "20px", "bottom": "20px", "left": "20px", "right": "20px"}
                    )
                    browser.close()
                return output_abs_path

            try:
                return _do_render()
            except Exception as first_exc:
                first_msg = str(first_exc).lower()
                missing_browser = (
                    "executable doesn't exist" in first_msg
                    or "browser has been closed" in first_msg
                    or "please run the following command" in first_msg
                )
                if not missing_browser:
                    raise

                # 首次发现缺少浏览器内核时自动安装并重试一次
                PDFGenerator._ensure_playwright_chromium()
                return _do_render()
        finally:
            # 清理临时HTML文件
            if os.path.exists(tmp_file.name):
                os.remove(tmp_file.name)

    @staticmethod
    def html_to_pdf(html_content: str, output_path: str = "output.pdf") -> str:
        """
        将 HTML 字符串转换并保存为 PDF 文件。

        :param html_content: 要转换的完整HTML文本
        :param output_path: 生成的 PDF 文件的本地保存路径
        :return: 保存的 PDF 绝对路径
        """
        output_abs_path = os.path.abspath(output_path)

        # 优先使用 WeasyPrint，失败后再降级 Playwright。
        try:
            return PDFGenerator._render_by_weasyprint(html_content, output_abs_path)
        except Exception as weasy_exc:
            try:
                return PDFGenerator._render_by_playwright(html_content, output_abs_path)
            except Exception as pw_exc:
                weasy_msg = str(weasy_exc).strip() or weasy_exc.__class__.__name__
                pw_msg = str(pw_exc).strip() or pw_exc.__class__.__name__
                raise RuntimeError(
                    "PDF 生成失败。WeasyPrint 渲染失败，且 Playwright 降级也失败。"
                    f" WeasyPrint: {weasy_msg}; Playwright: {pw_msg}."
                    " 请在服务器执行：pip install weasyprint 或 python -m playwright install chromium"
                ) from pw_exc
