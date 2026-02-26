import os
import sys
import json
from pathlib import Path
from typing import List, Optional, Dict

# 导入三个脚本的函数
from getWiki import ConfluenceExtractor, save_to_file
from analyzeByDify import process_wiki_file
from report import (
    read_csv_files, clean_data, generate_designer_summary, 
    generate_project_summary, generate_department_summary,
    generate_week_summary, generate_insights, generate_markdown_report,
    save_report
)


class WikiReportGenerator:
    """Wiki页面报告生成器"""
    
    def __init__(
        self,
        base_url: str,
        username: str,
        api_token: str,
        dify_api_key: str,
        wiki_dir: str = "wiki",
        analyze_dir: str = "analyze",
        result_dir: str = "result"
    ):
        """
        初始化报告生成器
        
        Args:
            base_url: Confluence基础URL
            username: Confluence用户名
            api_token: Confluence API令牌
            dify_api_key: Dify API密钥
            wiki_dir: Wiki文件存储目录
            analyze_dir: 分析文件存储目录
            result_dir: 结果文件存储目录
        """
        self.base_url = base_url
        self.username = username
        self.api_token = api_token
        self.dify_api_key = dify_api_key
        self.wiki_dir = wiki_dir
        self.analyze_dir = analyze_dir
        self.result_dir = result_dir
        
        # 确保目录存在
        os.makedirs(wiki_dir, exist_ok=True)
        os.makedirs(analyze_dir, exist_ok=True)
        os.makedirs(result_dir, exist_ok=True)
        
    def fetch_wiki_content(self, page_id: str) -> Optional[str]:
        """从Confluence获取Wiki页面内容"""
        print(f"\n{'='*60}")
        print(f"步骤1: 从Confluence获取页面 {page_id}")
        print('='*60)
        
        extractor = ConfluenceExtractor(self.base_url, self.username, self.api_token)
        content = extractor.get_page_content(page_id)
        
        if not content:
            print(f"错误: 无法获取页面 {page_id} 的内容")
            return None
        
        # 保存到文件
        filepath = save_to_file(content, folder=self.wiki_dir)
        print(f"✓ Wiki内容已保存到: {filepath}")
        
        return filepath
    
    def analyze_with_dify(self, wiki_file_path: str) -> Optional[str]:
        """使用Dify分析Wiki内容"""
        print(f"\n{'='*60}")
        print("步骤2: 使用Dify分析内容")
        print('='*60)
        
        result = process_wiki_file(
            api_key=self.dify_api_key,
            file_path=wiki_file_path,
            output_dir=self.analyze_dir
        )
        
        if not result:
            print("错误: Dify分析失败")
            return None
        
        return result  # process_wiki_file现在返回CSV路径
    
    def generate_report_from_csv(self, csv_file_path: str, page_id: str) -> Optional[str]:
        """从CSV文件生成报告"""
        print(f"\n{'='*60}")
        print("步骤3: 生成分析报告")
        print('='*60)
        
        # 读取数据
        df = read_csv_files([csv_file_path])
        
        if df.empty:
            print("错误: CSV文件为空或读取失败")
            return None
        
        print(f"✓ 读取 {len(df)} 行数据")
        
        # 数据清洗
        df = clean_data(df)
        
        # 生成各类汇总
        designer_summary = generate_designer_summary(df)
        project_summary = generate_project_summary(df)
        department_summary = generate_department_summary(df)
        week_summary = generate_week_summary(df)
        insights = generate_insights(df)
        
        print(f"✓ 生成 {len(designer_summary)} 位设计师的汇总")
        print(f"✓ 生成 {len(project_summary)} 个项目的汇总")
        print(f"✓ 生成 {len(department_summary)} 个部门的汇总")
        
        # 生成Markdown报告
        markdown_report = generate_markdown_report(
            designer_summary, project_summary, department_summary,
            week_summary, insights, [csv_file_path], [page_id]
        )
        
        # 保存报告
        report_path = save_report(markdown_report, output_dir=self.result_dir)
        
        if report_path:
            print(f"\n{'='*60}")
            print("🎉 报告生成成功!")
            print(f"📄 报告位置: {report_path}")
            print('='*60)
            
            # 显示报告预览
            self.preview_report(report_path)
            
            return report_path
        
        return None
    
    def preview_report(self, report_path: str):
        """预览报告内容"""
        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            print("\n📋 报告预览:")
            print("-" * 50)
            for i, line in enumerate(lines[:20]):  # 显示前20行
                if i < 20:
                    print(line.rstrip())
            print("...")
            print("-" * 50)
        except Exception as e:
            print(f"预览报告时出错: {e}")
    
    def generate_report_for_page(self, page_id: str, clean_files: bool = False) -> Optional[str]:
        """
        为指定页面ID生成报告
        
        Args:
            page_id: Confluence页面ID
            clean_files: 是否清理中间文件
            
        Returns:
            报告文件路径，如果失败则返回None
        """
        print(f"\n🚀 开始为页面 {page_id} 生成报告...")
        
        # 步骤1: 获取Wiki内容
        wiki_file_path = self.fetch_wiki_content(page_id)
        if not wiki_file_path:
            return None
        
        # 步骤2: Dify分析
        csv_file_path = self.analyze_with_dify(wiki_file_path)
        if not csv_file_path:
            return None
        
        # 步骤3: 生成报告
        report_path = self.generate_report_from_csv(csv_file_path, page_id)
        
        return report_path


def main():
    """主函数 - 完全从配置文件运行"""
    config_file = "config.json"
    
    # 检查配置文件是否存在
    if not os.path.exists(config_file):
        print(f"错误: 配置文件 {config_file} 不存在")
        print("正在创建默认配置文件...")
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)
        
        print(f"已创建配置文件: {config_file}")
        print("请编辑此文件，然后重新运行程序")
        return
    
    # 加载配置
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        print(f"读取配置文件时出错: {e}")
        return
    
    # 检查必需配置
    required_keys = ['base_url', 'username', 'api_token', 'dify_api_key', 'page_ids']
    missing_keys = [key for key in required_keys if key not in config]
    
    if missing_keys:
        print(f"错误: 配置文件缺少必需的键: {', '.join(missing_keys)}")
        return
    
    print("="*60)
    print("Wiki页面报告生成器")
    print("="*60)
    print(f"Confluence URL: {config['base_url']}")
    print(f"用户名: {config['username']}")
    print(f"API令牌: {config['api_token'][:15]}...")
    print(f"Dify API密钥: {config['dify_api_key'][:10]}...")
    print(f"清理中间文件: {config.get('clean_files', False)}")
    print(f"页面ID: {config['page_ids']}")
    print("="*60)
    
    # 创建报告生成器
    generator = WikiReportGenerator(
        base_url=config['base_url'],
        username=config['username'],
        api_token=config['api_token'],
        dify_api_key=config['dify_api_key']
    )
    
    # 处理页面ID
    page_ids = config['page_ids'] if isinstance(config['page_ids'], list) else [config['page_ids']]
    clean_files = config.get('clean_files', False)
    
    reports = []
    for i, page_id in enumerate(page_ids, 1):
        print(f"\n📝 处理页面 {i}/{len(page_ids)}: {page_id}")
        
        report_path = generator.generate_report_for_page(page_id, clean_files)
        if report_path:
            reports.append(report_path)
            print(f"✅ 页面 {page_id} 处理完成")
        else:
            print(f"❌ 页面 {page_id} 处理失败")
        
        if i < len(page_ids):
            print("\n" + "="*80 + "\n")
    
    print("\n" + "="*60)
    print("📊 处理完成!")
    print("="*60)
    print(f"总页面数: {len(page_ids)}")
    print(f"成功生成: {len(reports)}")
    print(f"失败: {len(page_ids) - len(reports)}")
    
    if reports:
        print("\n生成的报告:")
        for report in reports:
            print(f"  📄 {report}")


if __name__ == "__main__":
    main()