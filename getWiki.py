import requests
from bs4 import BeautifulSoup
import re
import json
import os
import time
from typing import List, Optional, Dict, Any
from html.parser import HTMLParser

def extract_page_id(page_id_or_url: str) -> str:
    """
    支持直接输入页面ID或URL，自动提取ID
    """
    # 如果是纯数字，直接返回
    if page_id_or_url.isdigit():
        return page_id_or_url
    # 尝试从URL中提取ID
    match = re.search(r'/pages/(\d+)', page_id_or_url)
    if match:
        return match.group(1)
    # 兼容旧格式
    match = re.search(r'pageId=(\d+)', page_id_or_url)
    if match:
        return match.group(1)
    # 兼容新版URL
    match = re.search(r'/(\d+)(?:/|$)', page_id_or_url)
    if match:
        return match.group(1)
    # 默认返回原始输入
    return page_id_or_url

class ConfluenceExtractor:
    def __init__(self, base_url: str, username: str, api_token: str, max_retries: int = 2):
        """
        初始化Confluence连接
        :param base_url: Confluence基础URL (如: https://your-domain.atlassian.net/wiki)
        :param username: 邮箱地址
        :param api_token: API令牌 (从https://id.atlassian.com/manage-profile/security/api-tokens获取)
        :param max_retries: 最大重试次数
        """
        self.base_url = base_url.rstrip('/')
        self.auth = (username, api_token)
        self.max_retries = max_retries
        self.headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    
    def get_page_content(self, page_id: str) -> Optional[dict]:
        """
        通过页面ID获取文章内容，支持重试机制
        """
        # 支持直接输入URL，自动提取ID
        page_id = extract_page_id(page_id)

        # 优先使用 v2 API，拿 storage 格式并转换为 Markdown
        url_v2 = f"{self.base_url}/api/v2/pages/{page_id}"
        params_v2 = {"body-format": "storage"}

        # 兼容旧接口兜底
        url_v1 = f"{self.base_url}/rest/api/content/{page_id}"
        params_v1 = {"expand": "body.view,version"}

        for attempt in range(self.max_retries + 1):
            try:
                response = requests.get(
                    url_v2,
                    auth=self.auth,
                    headers=self.headers,
                    params=params_v2,
                    timeout=30
                )

                if response.status_code == 404:
                    # 某些环境没有 v2，回退到 v1
                    response = requests.get(
                        url_v1,
                        auth=self.auth,
                        headers=self.headers,
                        params=params_v1,
                        timeout=30
                    )

                response.raise_for_status()
                data = response.json()

                # v2: body.storage.value；v1: body.view.value
                html_content = (
                    ((data.get("body") or {}).get("storage") or {}).get("value")
                    or ((data.get("body") or {}).get("view") or {}).get("value")
                    or ""
                )

                markdown_content = html_to_md(html_content)
                if not markdown_content:
                    markdown_content = self.extract_plain_text(html_content)

                title = data.get("title", f"page_{page_id}")
                version = (
                    (data.get("version") or {}).get("number")
                    if isinstance(data.get("version"), dict)
                    else data.get("version", "")
                )

                links = data.get("_links") if isinstance(data, dict) else {}
                base = links.get("base") if isinstance(links, dict) else ""
                webui = links.get("webui") if isinstance(links, dict) else ""
                page_url = f"{base}{webui}" if base and webui else f"{self.base_url}/pages/viewpage.action?pageId={page_id}"

                return {
                    "title": title,
                    "content": markdown_content,  # 这里改为 Markdown 内容
                    "version": version,
                    "url": page_url,
                    "page_id": page_id
                }

            except requests.exceptions.RequestException as e:
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt
                    print(f"请求错误，{wait_time}秒后重试: {e}")
                    time.sleep(wait_time)
                else:
                    print(f"获取页面 {page_id} 失败，已达到最大重试次数: {e}")
                    return None
            except KeyError as e:
                print(f"解析响应数据错误: {e}")
                return None
            except Exception as e:
                print(f"未知错误: {e}")
                return None

        return None
    
    def batch_get_pages(self, page_ids: List[str]) -> List[dict]:
        """
        批量获取多个页面的内容
        """
        results = []
        total = len(page_ids)
        
        for i, page_id in enumerate(page_ids, 1):
            real_page_id = extract_page_id(page_id)
            print(f"正在获取页面 {i}/{total}: {page_id}...")
            content = self.get_page_content(real_page_id)
            if content:
                results.append(content)
                print(f"  成功: {content['title']}")
            else:
                print(f"  失败: {page_id}")
            
            # 添加短暂延迟避免请求过快
            if i < total:
                time.sleep(0.5)
        
        return results
    
    def search_pages(self, query: str, space_key: Optional[str] = None, limit: int = 25):
        """
        搜索页面
        """
        url = f"{self.base_url}/rest/api/content/search"
        cql_query = f'title ~ "{query}"'
        if space_key:
            cql_query += f' and space = "{space_key}"'
            
        params = {
            'cql': cql_query,
            'limit': limit,
            'expand': 'content.id,content.title'
        }
        
        try:
            response = requests.get(
                url, 
                auth=self.auth, 
                headers=self.headers,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            
            return response.json()['results']
            
        except requests.exceptions.RequestException as e:
            print(f"搜索错误: {e}")
            return []
    
    def extract_plain_text(self, html_content: str) -> str:
        """
        从HTML中提取纯文本，移除所有标签
        """
        # 使用BeautifulSoup解析HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 移除所有脚本和样式标签
        for script in soup(["script", "style", "nav", "header", "footer", "aside"]):
            script.decompose()
        
        # 获取文本
        text = soup.get_text()
        
        # 清理文本
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        # 移除多余的空白字符
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()

class TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables = []
        self.current_table = None
        self.current_row = None
        self.current_cell = None
        self.in_table = False

    def handle_starttag(self, tag, _):
        if tag == "table":
            self.in_table = True
            self.current_table = []
        elif tag == "tr" and self.in_table:
            self.current_row = []
        elif tag in ("th", "td") and self.current_row is not None:
            self.current_cell = {"tag": tag, "content": ""}

    def handle_endtag(self, tag):
        if tag == "table" and self.in_table:
            if self.current_table:
                self.tables.append(self.current_table)
            self.current_table = None
            self.in_table = False
        elif tag == "tr" and self.current_row is not None:
            if self.current_row:
                self.current_table.append(self.current_row)
            self.current_row = None
        elif tag in ("th", "td") and self.current_cell is not None:
            self.current_row.append(self.current_cell)
            self.current_cell = None

    def handle_data(self, data):
        if self.current_cell is not None:
            self.current_cell["content"] += data.strip()


def table_to_markdown(table) -> str:
    if not table:
        return ""

    for row in table:
        for cell in row:
            cell["content"] = re.sub(r"\s+", " ", cell["content"]).strip()

    max_cols = max(len(row) for row in table)
    for row in table:
        while len(row) < max_cols:
            row.append({"tag": "td", "content": ""})

    has_header = table and all(cell["tag"] == "th" for cell in table[0])

    lines = []
    for i, row in enumerate(table):
        cells = [cell["content"] for cell in row]
        lines.append("| " + " | ".join(cells) + " |")
        if i == 0 and has_header:
            lines.append("| " + " | ".join(["---"] * max_cols) + " |")

    return "\n".join(lines)


def normalize_html(html: str) -> str:
    h = html

    h = re.sub(
        r"<ac:layout[^>]*>|</ac:layout[^>]*>|<ac:layout-section[^>]*>|</ac:layout-section>|<ac:layout-cell>|</ac:layout-cell>",
        "<div>",
        h,
        flags=re.I,
    )
    h = re.sub(r"<colgroup>[\s\S]*?</colgroup>|<col[^>]*/?>", "", h, flags=re.I)

    h = re.sub(
        r"<ac:structured-macro[^>]*ac:name=\"code\"[^>]*>([\s\S]*?)</ac:structured-macro>",
        lambda m: "```\n"
        + (
            re.search(r"<!\[CDATA\[([\s\S]*?)\]\]>", m.group(1), re.I).group(1)
            if re.search(r"<!\[CDATA\[", m.group(1), re.I)
            else re.sub(r"<[^>]+>", "", m.group(1))
        )
        + "\n```",
        h,
        flags=re.I,
    )

    h = re.sub(
        r"<ac:structured-macro[^>]*ac:name=\"(?:info|note|warning|tip|panel)\"[^>]*>([\s\S]*?)</ac:structured-macro>",
        lambda m: "> "
        + re.sub(
            r"<[^>]+>",
            "",
            re.search(r"<ac:rich-text-body>([\s\S]*?)</ac:rich-text-body>", m.group(1), re.I).group(1)
            if re.search(r"<ac:rich-text-body>", m.group(1), re.I)
            else m.group(1),
        ).strip(),
        h,
        flags=re.I,
    )

    h = re.sub(r"<ac:task-list>", "<ul>", h, flags=re.I)
    h = re.sub(r"</ac:task-list>", "</ul>", h, flags=re.I)
    h = re.sub(
        r"<ac:task>([\s\S]*?)</ac:task>",
        lambda m: (
            "<li>"
            + ("[x] " if re.search(r"<ac:task-status>([\s\S]*?)</ac:task-status>", m.group(1), re.I)
               and "complete" in re.search(r"<ac:task-status>([\s\S]*?)</ac:task-status>", m.group(1), re.I).group(1).lower()
               else "[ ] ")
            + re.sub(
                r"<[^>]+>",
                "",
                re.search(r"<ac:task-body>([\s\S]*?)</ac:task-body>", m.group(1), re.I).group(1)
                if re.search(r"<ac:task-body>", m.group(1), re.I)
                else m.group(1),
            )
            + "</li>"
        ),
        h,
        flags=re.I,
    )

    h = re.sub(r"</?(?:ac|ri):[^>]*>|<!\[CDATA\[|\]\]>", "", h, flags=re.I)
    h = re.sub(r"<ac:parameter[^>]*>[\s\S]*?</ac:parameter>", "", h, flags=re.I)
    h = re.sub(r"<ac:rich-text-body>|</ac:rich-text-body>", "", h, flags=re.I)

    return h


def html_to_md(html: str) -> str:
    h = normalize_html(html)

    parser = TableParser()
    parser.feed(h)
    for table in parser.tables:
        md_table = table_to_markdown(table)
        table_match = re.search(r"<table[^>]*>[\s\S]*?</table>", h, flags=re.I)
        if table_match:
            h = h.replace(table_match.group(0), f"\n{md_table}\n", 1)

    for i in range(1, 7):
        h = re.sub(
            rf"<h{i}[^>]*>(.*?)</h{i}>",
            lambda m, level=i: "\n" + "#" * level + " " + re.sub(r"<[^>]+>", "", m.group(1)).strip() + "\n",
            h,
            flags=re.S | re.I,
        )

    h = re.sub(r"<strong>(.*?)</strong>", r"**\1**", h, flags=re.S | re.I)
    h = re.sub(r"<em>(.*?)</em>", r"*\1*", h, flags=re.S | re.I)
    h = re.sub(r"<a[^>]*href=\"([^\"]*)\"[^>]*>(.*?)</a>", r"[\2](\1)", h, flags=re.S | re.I)
    h = re.sub(r"<li[^>]*>(.*?)</li>", lambda m: "- " + re.sub(r"<[^>]+>", "", m.group(1)).strip(), h, flags=re.S | re.I)

    h = re.sub(r"</?table[^>]*>|</?tbody>|</?thead>|</?tr[^>]*>|</?th[^>]*>|</?td[^>]*>", "", h, flags=re.I)
    h = re.sub(r"</?[ou]l[^>]*>", "\n", h, flags=re.I)
    h = re.sub(r"<br\s*/?>", "\n", h, flags=re.I)
    h = re.sub(r"</?p[^>]*>|</?div[^>]*>|</?span[^>]*>", "\n", h, flags=re.I)
    h = re.sub(r"<[^>]+>", "", h)
    h = re.sub(r"\n{3,}", "\n\n", h)

    h = re.sub(r"&nbsp;", " ", h)
    h = re.sub(r"&lt;", "<", h)
    h = re.sub(r"&gt;", ">", h)
    h = re.sub(r"&amp;", "&", h)
    h = re.sub(r"&ldquo;|&rdquo;", "\"", h)
    h = re.sub(r"&lsquo;|&rsquo;", "'", h)
    h = re.sub(r"&rarr;", "→", h)
    h = re.sub(r"&middot;", "·", h)

    return h.strip()

def load_config(config_file: str = "config.json") -> Dict[str, Any]:
    """
    加载配置文件
    """
    if not os.path.exists(config_file):
        print(f"配置文件 {config_file} 不存在!")
        # 创建默认配置文件
        default_config = {
            "base_url": "https://your-domain.atlassian.net/wiki",
            "username": "your-email@example.com",
            "api_token": "your-api-token-here",
            "dify_api_key": "",
            "page_ids": ["123456789"],
            "max_retries": 2,
            "clean_files": False
        }
        
        with open(config_file, 'w', encoding='utf-8-sig') as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)
        
        print(f"已创建默认配置文件 {config_file}，请修改配置后重新运行程序。")
        exit(1)
    
    try:
        with open(config_file, 'r', encoding='utf-8-sig') as f:
            config = json.load(f)
        
        # 验证必要配置项
        required_keys = ["base_url", "username", "api_token", "page_ids"]
        for key in required_keys:
            if key not in config:
                raise ValueError(f"配置文件中缺少必要的键: {key}")
        
        return config
    except json.JSONDecodeError as e:
        print(f"配置文件格式错误: {e}")
        exit(1)
    except Exception as e:
        print(f"加载配置文件失败: {e}")
        exit(1)

def clean_old_files(folder: str = "wiki") -> None:
    """
    清理旧的wiki文件
    """
    if os.path.exists(folder):
        count = 0
        for filename in os.listdir(folder):
            filepath = os.path.join(folder, filename)
            try:
                if os.path.isfile(filepath):
                    os.unlink(filepath)
                    count += 1
            except Exception as e:
                print(f"删除文件 {filepath} 时出错: {e}")
        
        print(f"已清理 {count} 个旧文件")
    else:
        print(f"文件夹 {folder} 不存在，无需清理")

def sanitize_filename(filename: str) -> str:
    """
    创建安全的文件名（移除非法字符）
    """
    # 移除非法字符
    illegal_chars = r'<>:"/\|?*'
    for char in illegal_chars:
        filename = filename.replace(char, '')
    
    # 替换空格为下划线并限制长度
    filename = filename.replace(' ', '_')[:100]
    
    return filename

def save_to_file(content: dict, folder: str = "wiki") -> str:
    """
    保存内容到文件
    :param content: 页面内容字典
    :param folder: 保存文件夹，默认为"wiki"
    :return: 保存的文件路径
    """
    # 确保wiki文件夹存在
    if not os.path.exists(folder):
        os.makedirs(folder)
        print(f"已创建文件夹: {folder}")
    
    # 创建安全的文件名
    safe_title = sanitize_filename(content['title'])
    
    filename = f"{safe_title}_{content['page_id']}.txt"
    filepath = os.path.join(folder, filename)
    
    try:
        with open(filepath, 'w', encoding='utf-8-sig') as f:
            f.write(f"页面ID: {content['page_id']}\n")
            f.write(f"标题: {content['title']}\n")
            f.write(f"版本: {content['version']}\n")
            f.write(f"URL: {content['url']}\n")
            f.write(f"提取时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("-" * 80 + "\n\n")
            f.write(content['content'])
        
        print(f"内容已保存到: {filepath}")
        return filepath
    except Exception as e:
        print(f"保存文件失败: {e}")
        return ""

def save_batch_summary(contents: List[dict], folder: str = "wiki") -> str:
    """
    保存批量处理的摘要信息
    """
    if not os.path.exists(folder):
        os.makedirs(folder)
    
    summary_file = os.path.join(folder, "batch_summary.json")
    
    summary = {
        "total_pages": len(contents),
        "extraction_time": time.strftime('%Y-%m-%d %H:%M:%S'),
        "pages": []
    }
    
    for content in contents:
        safe_title = sanitize_filename(content['title'])
        summary["pages"].append({
            "page_id": content["page_id"],
            "title": content["title"],
            "version": content["version"],
            "url": content["url"],
            "content_length": len(content["content"]),
            "file_name": f"{safe_title}_{content['page_id']}.txt"
        })
    
    try:
        with open(summary_file, 'w', encoding='utf-8-sig') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        print(f"批量处理摘要已保存到: {summary_file}")
        return summary_file
    except Exception as e:
        print(f"保存摘要失败: {e}")
        return ""

def main():
    """
    主函数
    """
    print("=" * 60)
    print("Confluence 内容提取工具")
    print("=" * 60)
    
    # 加载配置文件
    print("\n[1/4] 加载配置文件...")
    config = load_config("config.json")
    
    BASE_URL = config["base_url"]
    USERNAME = config["username"]
    API_TOKEN = config["api_token"]
    PAGE_IDS = config["page_ids"]
    MAX_RETRIES = config.get("max_retries", 2)
    CLEAN_FILES = config.get("clean_files", False)
    
    # 清理旧文件（如果需要）
    if CLEAN_FILES:
        print(f"\n[2/4] 清理旧文件...")
        clean_old_files("wiki")
    
    # 初始化提取器
    print(f"\n[3/4] 初始化Confluence连接...")
    extractor = ConfluenceExtractor(
        base_url=BASE_URL,
        username=USERNAME,
        api_token=API_TOKEN,
        max_retries=MAX_RETRIES
    )
    
    print(f"连接地址: {BASE_URL}")
    print(f"最大重试次数: {MAX_RETRIES}")
    
    # 批量获取页面内容
    print(f"\n[4/4] 开始提取页面内容...")
    if PAGE_IDS:
        print(f"需要提取 {len(PAGE_IDS)} 个页面")
        contents = extractor.batch_get_pages(PAGE_IDS)
        
        if contents:
            success_count = len(contents)
            print(f"\n{'='*60}")
            print(f"提取完成! 成功获取 {success_count}/{len(PAGE_IDS)} 个页面")
            
            # 保存每个页面到文件
            saved_files = []
            for content in contents:
                filepath = save_to_file(content, folder="wiki")
                if filepath:
                    saved_files.append(filepath)
            
            # 保存批量处理摘要
            if saved_files:
                save_batch_summary(contents, folder="wiki")
                
                print(f"\n所有文件已保存到 wiki 文件夹:")
                for file in saved_files:
                    print(f"  {os.path.basename(file)}")
        else:
            print("所有页面提取都失败了，请检查网络连接和配置信息")
    else:
        print("配置文件中的 page_ids 为空，没有要提取的页面")
        print("\n是否要搜索页面? (y/n)")
        choice = input().strip().lower()
        
        if choice == 'y':
            search_query = input("请输入搜索关键词: ").strip()
            if search_query:
                print(f"\n正在搜索: {search_query}...")
                results = extractor.search_pages(search_query)
                
                if results:
                    print(f"\n找到 {len(results)} 个结果:")
                    for i, result in enumerate(results, 1):
                        print(f"{i}. {result['title']} (ID: {result['id']})")
                    
                    # 让用户选择要获取的页面
                    choice = input("\n请输入要获取的页面编号 (或输入q退出): ").strip()
                    if choice.isdigit():
                        index = int(choice) - 1
                        if 0 <= index < len(results):
                            page_id = extract_page_id(results[index].get('id', ''))
                            content = extractor.get_page_content(page_id)
                            
                            if content:
                                print(f"\n获取成功!")
                                print(f"标题: {content['title']}")
                                save_to_file(content, folder="wiki")
                        else:
                            print("无效的编号")
                else:
                    print("未找到相关页面")
    
    print(f"\n{'='*60}")
    print("程序执行完成")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断程序执行")
    except Exception as e:
        print(f"\n程序执行出错: {e}")