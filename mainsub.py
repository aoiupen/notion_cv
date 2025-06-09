import os
import asyncio
import sys
import re
import requests
from bs4 import BeautifulSoup
from notion_client import AsyncClient
from playwright.async_api import async_playwright
from dotenv import load_dotenv

# --- 1. 설정: .env 파일에서 환경변수 불러오기 ---
load_dotenv()

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
PAGE_ID = os.getenv("PAGE_ID")
OUTPUT_PDF_NAME = "My_Portfolio_Final.pdf"
PAGE_TITLE = os.getenv("PAGE_TITLE", "포트폴리오")

# 환경변수가 제대로 로드되었는지 확인
if not NOTION_API_KEY or not PAGE_ID:
    print("❌ 오류: .env 파일에 NOTION_API_KEY와 PAGE_ID를 설정해주세요.")
    sys.exit(1)

# 표 스타일 매핑 딕셔너리
NOTION_COLOR_MAP = {
    'default': '#000000',
    'gray': '#787774',
    'brown': '#9F6B53',
    'orange': '#D9730D',
    'yellow': '#CB912F',
    'green': '#448361',
    'blue': '#337EA9',
    'purple': '#9065B0',
    'pink': '#C14C8A',
    'red': '#D44C47'
}
NOTION_BG_MAP = {
    'default': '#FFFFFF',
    'gray_background': '#F1F1EF',
    'brown_background': '#F4EEEE',
    'orange_background': '#FAEBDD',
    'yellow_background': '#FBF3DB',
    'green_background': '#EDF3EC',
    'blue_background': '#E7F3F8',
    'purple_background': '#F6F3F9',
    'pink_background': '#FAF1F5',
    'red_background': '#FDEBEC'
}

CELL_PADDING_PX = 16  # 좌우 합계 (8px + 8px)
TABLE_TOTAL_WIDTH = 100  # % 기준

def get_styles():
    """PDF에 적용될 CSS 스타일을 반환합니다. (노션 줄간격/구분선/문단 간격 참고)"""
    return """
    /* --- 폰트 및 기본 설정 --- */
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css');
    @page { size: A4; margin: 2cm; }
    body {
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, 'Helvetica Neue', 'Segoe UI', 'Apple SD Gothic Neo', 'Noto Sans KR', 'Malgun Gothic', 'Apple Color Emoji', 'Segoe UI Emoji', 'Segoe UI Symbol', sans-serif;
        line-height: 1.7;
        color: #333333;
        -webkit-font-smoothing: antialiased;
        font-size: 10.5pt; 
    }
    h1 { font-size: 2.5em; margin: 1.2em 0 0.5em 0; }
    h2 { font-size: 1.8em; margin: 1.1em 0 0.4em 0; }
    h3 { font-size: 1.2em; margin: 0.9em 0 0.3em 0; }
    p { margin: 0.35em 0 0.35em 0; }
    ul, ol { margin: 0.25em 0 0.25em 1.5em; padding-left: 1.2em; }
    li { margin: 0.13em 0; line-height: 1.7; }
    li > ul, li > ol { margin: 0.13em 0 0.13em 1.2em; }
    .nested-list { margin-left: 1.2em; margin-top: 0.13em; }
    .nested-list li { margin: 0.13em 0; }
    hr { border: 0; border-top: 1px solid #eaeaea; margin: 0.9em 0 0.9em 0; }
    blockquote { border-left: 3px solid #ccc; padding-left: 1em; color: #666; margin: 0.5em 0; }
    pre { background-color: #f8f8f8; padding: 1.2em; border-radius: 6px; white-space: pre-wrap; word-wrap: break-word; font-size: 0.9em; margin: 0.5em 0; }
    code { font-family: 'D2Coding', 'Consolas', 'Monaco', monospace; }
    a { color: #0066cc; text-decoration: none; }
    a:hover { text-decoration: underline; }
    img { max-width: 600px !important; max-height: 350px !important; object-fit: contain; margin: 1em auto; display: block; }
    .large-diagram { max-width: 700px !important; max-height: 400px !important; }
    figure { margin: 1.2em 0; width: 100%; }
    details { border: 1px solid #eaeaea; border-radius: 6px; padding: 1.2em; margin: 0.7em 0; }
    summary { font-weight: 600; cursor: default; }
    table { width: 100%; border-collapse: collapse; margin: 1em 0; font-size: 0.9em; table-layout: fixed; }
    th, td { border: 1px solid #ddd; padding: 0.5em 0.8em; text-align: left; vertical-align: top; word-wrap: break-word; word-break: break-all; white-space: pre-line; }
    th { background-color: #f2f2f2; font-weight: 600; }
    """

def extract_page_title(page_info):
    """Notion 페이지 정보에서 제목을 추출합니다."""
    try:
        properties = page_info.get('properties', {})
        for prop_name, prop_data in properties.items():
            if prop_data.get('type') == 'title':
                title_array = prop_data.get('title', [])
                if title_array:
                    return ''.join([item['plain_text'] for item in title_array])
        return PAGE_TITLE
    except Exception as e:
        print(f"제목 추출 중 오류: {e}")
        return PAGE_TITLE

def is_youtube_url(url):
    return (
        url.startswith("https://www.youtube.com/") or
        url.startswith("https://youtu.be/")
    )

def get_youtube_info(url):
    oembed_url = f"https://www.youtube.com/oembed?url={url}&format=json"
    try:
        resp = requests.get(oembed_url, timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            return {
                "title": data.get("title", "YouTube Video"),
                "favicon": "https://www.youtube.com/favicon.ico"
            }
    except Exception:
        pass
    return {
        "title": "YouTube Video",
        "favicon": "https://www.youtube.com/favicon.ico"
    }

def is_github_url(url):
    return url.startswith("https://github.com/")

def clean_github_title(title):
    title = re.sub(r'[-·]\s*GitHub.*$', '', title).strip()
    if ' - ' in title:
        parts = title.split(' - ')
        return parts[-1].strip()
    return title.strip()

def get_github_info(url):
    match = re.search(r'github\.com/([^/]+)/([^/?#]+)', url)
    if match:
        owner, repo = match.group(1), match.group(2)
        api_url = f'https://api.github.com/repos/{owner}/{repo}'
        try:
            resp = requests.get(api_url, timeout=3, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "title": data.get("name", f"{owner}/{repo}"),
                    "favicon": "https://github.com/fluidicon.png"
                }
        except Exception:
            pass
        return {
            "title": repo,
            "favicon": "https://github.com/fluidicon.png"
        }
    try:
        resp = requests.get(url, timeout=3, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            title = soup.title.string.strip() if soup.title and soup.title.string else "GitHub"
            title = clean_github_title(title)
            return {
                "title": title,
                "favicon": "https://github.com/fluidicon.png"
            }
    except Exception:
        pass
    return {
        "title": "GitHub",
        "favicon": "https://github.com/fluidicon.png"
    }

def rich_text_to_html(rich_text_array, process_nested_bullets=False):
    if not rich_text_array:
        return ""
    html = ""
    for chunk in rich_text_array:
        href = chunk.get("href")
        if href and is_youtube_url(href):
            info = get_youtube_info(href)
            html += (
                f'<span style="display:inline-flex;align-items:center;gap:0.4em;">'
                f'<img src="{info["favicon"]}" style="width:1em;height:1em;vertical-align:middle;">'
                f'<a href="{href}" target="_blank" style="font-weight:600;">YouTube</a>'
                f'</span>'
            )
        elif href and is_github_url(href):
            info = get_github_info(href)
            html += (
                f'<span style="display:inline-flex;align-items:center;gap:0.4em;">'
                f'<img src="{info["favicon"]}" style="width:1em;height:1em;vertical-align:middle;">'
                f'<a href="{href}" target="_blank" style="font-weight:600;">GitHub</a>'
                f'</span>'
            )
        else:
            text = chunk.get('plain_text', '').replace('\n', '<br>')
            html += apply_annotations(text, chunk)
    return html

def apply_annotations(text, chunk):
    if not text:
        return ""
    href = chunk.get('href')
    if href:
        return f'<a href="{href}">{text}</a>'
    annotations = chunk.get('annotations', {})
    if annotations.get('bold'): text = f'<strong>{text}</strong>'
    if annotations.get('italic'): text = f'<em>{text}</em>'
    if annotations.get('underline'): text = f'<u>{text}</u>'
    if annotations.get('strikethrough'): text = f'<s>{text}</s>'
    if annotations.get('code'): text = f'<code>{text}</code>'
    return text

def get_cell_style(cell, row_bg=None):
    if not cell:
        return ""
    first = cell[0] if cell else {}
    annotations = first.get('annotations', {})
    color = annotations.get('color', 'default')
    font_weight = 'bold' if annotations.get('bold') else 'normal'
    font_style = 'italic' if annotations.get('italic') else 'normal'
    text_color = NOTION_COLOR_MAP.get(color.replace('_background', ''), '#000')
    if 'background' in color:
        bg_color = NOTION_BG_MAP.get(color, '#fff')
    elif row_bg and row_bg != 'default':
        bg_color = NOTION_BG_MAP.get(row_bg, '#fff')
    else:
        bg_color = '#fff'
    style = f"color:{text_color};background:{bg_color};font-weight:{font_weight};font-style:{font_style};"
    return style

def get_plain_text_from_cell(cell):
    return ''.join([t.get('plain_text', '') for t in cell])

def estimate_column_widths_with_pixel_heuristic(table_rows):
    if not table_rows:
        return []
    col_lengths = []
    max_cols = max(len(row['table_row']['cells']) for row in table_rows)
    for col_idx in range(max_cols):
        max_length = 0
        for row in table_rows:
            cells = row['table_row']['cells']
            if col_idx < len(cells):
                cell_text = get_plain_text_from_cell(cells[col_idx])
                line_lengths = [len(line) for line in cell_text.split('\n')]
                cell_length = max(line_lengths) if line_lengths else 0
                max_length = max(max_length, cell_length)
        col_lengths.append(max_length)
    total_content_length = sum(col_lengths)
    if total_content_length == 0:
        return [100 / max_cols] * max_cols if max_cols > 0 else []
    PIXEL_PER_CHAR = 5.3
    MIN_COL_WIDTH_PX = 40
    estimated_px_widths = [max(MIN_COL_WIDTH_PX, length * PIXEL_PER_CHAR) for length in col_lengths]
    total_estimated_px_width = sum(estimated_px_widths)
    percent_widths = [(px_width / total_estimated_px_width) * 100 for px_width in estimated_px_widths]
    wrap_cols = set()
    for col_idx in range(max_cols):
        for row in table_rows:
            cells = row['table_row']['cells']
            if col_idx < len(cells):
                cell_text = get_plain_text_from_cell(cells[col_idx])
                if '\n' in cell_text:
                    wrap_cols.add(col_idx)
    current_sum = sum(percent_widths)
    remain = 100 - current_sum
    if remain > 0 and wrap_cols:
        add_per_col = remain / len(wrap_cols)
        for idx in wrap_cols:
            percent_widths[idx] += add_per_col
    current_sum2 = sum(percent_widths)
    if current_sum2 != 100 and percent_widths:
        diff = 100 - current_sum2
        percent_widths[0] += diff
    print(f"[최종 percent_widths with wrap 보정] {percent_widths}")
    return percent_widths

async def blocks_to_html(blocks, notion_client):
    """Notion 블록 리스트를 HTML로 변환합니다. (페이지 분류/나누기 없이 순서대로 출력)"""
    if not blocks:
        return ""
    html_parts = []
    i = 0
    while i < len(blocks):
        block = blocks[i]
        block_type = block['type']
        # 리스트 아이템 처리
        if block_type in ['bulleted_list_item', 'numbered_list_item']:
            list_tag = 'ul' if block_type == 'bulleted_list_item' else 'ol'
            list_items = []
            j = i
            while j < len(blocks) and blocks[j]['type'] == block_type:
                current_block = blocks[j]
                item_content = rich_text_to_html(
                    current_block[block_type]['rich_text'], 
                    process_nested_bullets=True
                )
                if current_block.get('has_children') and current_block.get('children'):
                    children_html = await blocks_to_html(current_block['children'], notion_client)
                    item_content += children_html
                list_items.append(f"<li>{item_content}</li>")
                j += 1
            list_html = f"<{list_tag}>{''.join(list_items)}</{list_tag}>"
            html_parts.append(list_html)
            i = j
            continue
        block_html = ""
        if block_type == 'heading_1':
            block_html = f"<h1>{rich_text_to_html(block['heading_1']['rich_text'])}</h1>"
        elif block_type == 'heading_2':
            h2_text = rich_text_to_html(block['heading_2']['rich_text'])
            block_html = f"<h2>{h2_text}</h2>"
        elif block_type == 'heading_3':
            h3_text = rich_text_to_html(block['heading_3']['rich_text'])
            block_html = f"<h3>{h3_text}</h3>"
        elif block_type == 'paragraph':
            text = rich_text_to_html(block['paragraph']['rich_text'])
            block_html = f"<p>{text if text.strip() else '&nbsp;'}</p>"
            if block.get('has_children') and block.get('children'):
                children_html = await blocks_to_html(block['children'], notion_client)
                block_html += f"<div style='margin-left: 2em;'>{children_html}</div>"
        elif block_type == 'image':
            image_data = block['image']
            url = ''
            if image_data.get('file'):
                url = image_data['file']['url']
            elif image_data.get('external'):
                url = image_data['external']['url']
            block_html = f"<figure><img src='{url}' alt='Image'></figure>"
        elif block_type == 'code':
            code_text = rich_text_to_html(block['code']['rich_text'])
            language = block['code'].get('language', '')
            block_html = f"<pre><code class='language-{language}'>{code_text}</code></pre>"
        elif block_type == 'divider':
            block_html = "<hr>"
        elif block_type == 'quote':
            block_html = f"<blockquote>{rich_text_to_html(block['quote']['rich_text'])}</blockquote>"
        elif block_type == 'toggle':
            summary = rich_text_to_html(block['toggle']['rich_text'])
            children_html = ""
            if block.get('has_children') and block.get('children'):
                children_html = await blocks_to_html(block['children'], notion_client)
            block_html = f"<details open><summary>{summary}</summary>{children_html}</details>"
        elif block_type == 'table':
            table_info = block['table']
            has_column_header = table_info.get('has_column_header', False)
            width_ratios = estimate_column_widths_with_pixel_heuristic(block.get('children', []))
            colgroup_html = ''
            if width_ratios:
                colgroup_html = '<colgroup>'
                for ratio in width_ratios:
                    colgroup_html += f'<col style="width:{ratio:.2f}%">'
                colgroup_html += '</colgroup>'
            table_html_content = f"<table>{colgroup_html}"
            if block.get('children'):
                for i_row, row_block in enumerate(block['children']):
                    if row_block['type'] == 'table_row':
                        cells = row_block['table_row']['cells']
                        row_tag = 'th' if has_column_header and i_row == 0 else 'td'
                        row_bg = row_block['table_row'].get('background', 'default')
                        table_html_content += f"<tr style='background:{NOTION_BG_MAP.get(row_bg, '#fff')}'>"
                        for col_idx, cell in enumerate(cells):
                            style = get_cell_style(cell, row_bg=row_bg)
                            width_style = f"width:{width_ratios[col_idx]:.2f}%;" if col_idx < len(width_ratios) else ''
                            table_html_content += f"<{row_tag} style='{style}{width_style}'>{rich_text_to_html(cell)}</{row_tag}>"
                        table_html_content += "</tr>"
            table_html_content += "</table>"
            block_html = table_html_content
        elif block_type == 'callout':
            callout = block['callout']
            icon_html = ''
            if callout.get('icon'):
                icon = callout['icon']
                if icon['type'] == 'emoji':
                    icon_html = f"{icon['emoji']} "
            callout_text = rich_text_to_html(callout['rich_text'])
            children_html = ''
            if block.get('has_children') and block.get('children'):
                children_html = await blocks_to_html(block['children'], notion_client)
            block_html = (
                f"<div style='background:#f7f6f3;border-radius:8px;padding:0.001em 1em;margin:0.7em 0;'>"
                f"{icon_html}{callout_text}{children_html}</div>"
            )
        html_parts.append(block_html)
        i += 1
    return ''.join(html_parts)

async def fetch_all_child_blocks(notion, block_id):
    blocks = []
    try:
        response = await notion.blocks.children.list(block_id=block_id, page_size=100)
        blocks.extend(response['.etc'])
        next_cursor = response.get('next_cursor')
        while next_cursor:
            response = await notion.blocks.children.list(
                block_id=block_id, 
                page_size=100, 
                start_cursor=next_cursor
            )
            blocks.extend(response['.etc'])
            next_cursor = response.get('next_cursor')
    except Exception as e:
        print(f"블록 가져오기 오류: {e}")
        return []
    for block in blocks:
        if block.get('has_children'):
            block['children'] = await fetch_all_child_blocks(notion, block['id'])
    return blocks

async def main():
    print("--- Notion to PDF (분류 없이 전체 인쇄) ---")
    notion = AsyncClient(auth=NOTION_API_KEY)
    try:
        page_info = await notion.pages.retrieve(page_id=PAGE_ID)
        page_title = extract_page_title(page_info)
        print(f"   페이지 제목: {page_title}")
    except Exception as e:
        print(f"   페이지 제목을 가져오지 못했습니다: {e}")
        page_title = PAGE_TITLE
    print(f"페이지({PAGE_ID}) 전체 블록을 가져오는 중...")
    blocks = await fetch_all_child_blocks(notion, PAGE_ID)
    print("HTML 변환 중...")
    content_html = await blocks_to_html(blocks, notion)
    styles = get_styles()
    full_html = f"""
    <!DOCTYPE html>
    <html lang=\"ko\">
    <head>
        <meta charset=\"UTF-8\">
        <title>{page_title}</title>
        <style>{styles}</style>
    </head>
    <body>
        <h1>{page_title}</h1>
        <div style='height: 1.5em;'></div>
        {content_html}
    </body>
    </html>
    """
    # HTML도 저장
    os.makedirs(".etc", exist_ok=True)
    html_path = os.path.join(".etc", "My_Portfolio_Final.html")
    pdf_path = os.path.join(".etc", OUTPUT_PDF_NAME)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(full_html)
    print("PDF 변환 중...")
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.set_content(full_html, wait_until="networkidle")
            await page.pdf(path=pdf_path, format="A4", print_background=True)
            await browser.close()
        print(f"\n🎉 성공! '{os.path.abspath(pdf_path)}' 파일이 생성되었습니다.")
    except Exception as e:
        print(f"\n❌ PDF 생성 중 오류 발생: {e}")
        print("   - playwright install 명령어를 실행했는지 확인하세요.")

if __name__ == "__main__":
    asyncio.run(main())



