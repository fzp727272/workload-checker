#!/usr/bin/env python3
"""
Wiki报告生成器 - 最小化版本
避免复杂的依赖问题
"""

import os
import sys
import json
import csv
import time
from datetime import datetime
from pathlib import Path

class SimpleReportGenerator:
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.config_file = self.base_dir / "simple_config.json"
        self.result_dir = self.base_dir / "simple_results"
        
        self.result_dir.mkdir(exist_ok=True)
    
    def load_config(self):
        """加载简单配置"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8-sig') as f:
                    return json.load(f)
            except:
                pass
        
        # 默认配置
        config = {
            "page_ids": ["2299133998"],
            "output_format": "csv"
        }
        
        with open(self.config_file, 'w', encoding='utf-8-sig') as f:
            json.dump(config, f, indent=2)
        
        return config
    
    def generate_sample_report(self):
        """生成示例报告"""
        print("生成示例报告...")
        
        # 创建示例CSV
        csv_file = self.result_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['设计组', '项目', '设计师', '工时(h)', '状态'])
            writer.writerow(['设计部', '项目A', '张三', '40', '已完成'])
            writer.writerow(['设计部', '项目B', '李四', '35', '进行中'])
            writer.writerow(['产品部', '项目C', '王五', '45', '待开始'])
            writer.writerow(['产品部', '项目D', '赵六', '30', '已完成'])
        
        print(f"✓ 报告已生成: {csv_file}")
        
        # 创建摘要文件
        summary_file = self.result_dir / f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(summary_file, 'w', encoding='utf-8-sig') as f:
            f.write(f"报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*50 + "\n")
            f.write("设计工时汇总\n")
            f.write("="*50 + "\n")
            f.write("总设计师: 4人\n")
            f.write("总项目数: 4个\n")
            f.write("总工时: 150小时\n")
            f.write("平均工时: 37.5小时/人\n")
        
        print(f"✓ 摘要已生成: {summary_file}")
        
        return str(csv_file), str(summary_file)
    
    def run(self):
        """运行生成器"""
        print("="*60)
        print("Wiki报告生成器 - 最小化版本")
        print("="*60)
        
        config = self.load_config()
        print(f"配置页面ID: {config.get('page_ids', [])}")
        
        # 生成报告
        csv_path, summary_path = self.generate_sample_report()
        
        print("\n" + "="*60)
        print("完成!")
        print(f"CSV文件: {csv_path}")
        print(f"摘要文件: {summary_path}")
        print("="*60)

if __name__ == "__main__":
    generator = SimpleReportGenerator()
    generator.run()
