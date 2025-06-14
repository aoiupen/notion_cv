import os
from pathlib import Path
from typing import Optional
from playwright.async_api import async_playwright

class HTML2PDFEngine:
    def __init__(self, css_path: str = "portfolio_style.css", output_dir: str = ".etc"):
        self.css_path = Path(css_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def _load_css_styles(self) -> str:
        try:
            with open(self.css_path, encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"CSS 파일 읽기 오류: {e}")
            return self._get_default_css()

    def _get_default_css(self) -> str:
        return """
        @page { size: A4; margin: 2cm; }
        body { font-family: 'Pretendard', sans-serif; line-height: 1.6; }
        h1 { font-size: 2.5em; margin: 1.2em 0 0.1em 0; }
        h2 { font-size: 1.8em; margin: 1.1em 0 0.4em 0; }
        h3 { font-size: 1.2em; margin: 0.9em 0 0.3em 0; }
        """

    def generate_full_html(self, title: str, content: str) -> str:
        css_styles = self._load_css_styles()
        return f"""
<!DOCTYPE html>
<html lang=\"ko\">
<head>
    <meta charset=\"UTF-8\">
    <title>{title}</title>
    <style>{css_styles}</style>
</head>
<body>
    {'<h1>' + title + '</h1><div style="height: 1.5em;"></div>' if title else ''}
    {content}
</body>
</html>
"""

    async def html_to_pdf(self, html: str, output_filename: str) -> Optional[str]:
        pdf_path = self.output_dir / output_filename
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.set_content(html, wait_until="networkidle")
                await page.pdf(path=str(pdf_path), format="A4", print_background=True)
                await browser.close()
            print(f"✅ PDF 생성 완료: {pdf_path}")
            return str(pdf_path)
        except Exception as e:
            print(f"❌ PDF 생성 중 오류: {e}")
            return None 