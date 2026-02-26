#!/usr/bin/env python3
"""
继续修复脚本 - 运行剩余步骤
"""

import os
import sys
import json
import subprocess
import platform
from datetime import datetime
from pathlib import Path

def generate_diagnostic_report():
    """生成诊断报告"""
    print("\n" + "="*60)
    print("生成系统诊断报告")
    print("="*60)
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "platform": platform.platform(),
        "python_version": sys.version,
        "python_executable": sys.executable,
        "system": platform.system(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "env_path": os.environ.get("PATH", "").split(os.pathsep)[:5],
        "working_directory": os.getcwd(),
    }
    
    report_file = "diagnostic_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"✓ 诊断报告已保存到: {report_file}")
    
    # 显示关键信息
    print("\n关键信息:")
    print(f"  操作系统: {report['platform']}")
    print(f"  Python路径: {report['python_executable']}")
    print(f"  Python版本: {report['python_version'].split()[0]}")
    print(f"  工作目录: {report['working_directory']}")

def install_dependencies_safely():
    """安全安装依赖"""
    print("\n" + "="*60)
    print("安装项目依赖")
    print("="*60)
    
    # 要安装的包（使用兼容版本）
    packages = [
        "Flask==2.3.3",
        "requests==2.31.0",
        "pandas==1.5.3",
        "beautifulsoup4==4.12.2",
        "lxml==4.9.3",
        "openpyxl==3.1.2",
    ]
    
    success_count = 0
    fail_count = 0
    
    # 逐个安装，避免一个失败影响全部
    for package in packages:
        print(f"\n安装 {package}...")
        try:
            result = subprocess.run(
                [
                    sys.executable, "-m", "pip", "install",
                    "--no-warn-script-location",
                    "--timeout", "30",
                    package
                ],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                print(f"✓ {package} 安装成功")
                success_count += 1
            else:
                print(f"✗ {package} 安装失败")
                print(f"  错误: {result.stderr[:200]}")
                fail_count += 1
                
        except subprocess.TimeoutExpired:
            print(f"⚠ {package} 安装超时")
            fail_count += 1
        except Exception as e:
            print(f"⚠ {package} 安装异常: {e}")
            fail_count += 1
    
    print(f"\n安装结果: 成功 {success_count}, 失败 {fail_count}")
    return fail_count == 0

def main():
    """主函数"""
    print("="*60)
    print("继续修复脚本 - 运行剩余步骤")
    print("="*60)
    
    # 生成诊断报告
    generate_diagnostic_report()
    
    # 询问是否安装依赖
    print("\n" + "="*60)
    print("是否安装完整依赖?")
    print("输入 'y' 安装，输入 'n' 跳过")
    print("="*60)
    
    choice = input("选择 (y/n): ").strip().lower()
    if choice == 'y':
        install_dependencies_safely()
    
    print("\n" + "="*60)
    print("继续修复完成!")
    print("="*60)

if __name__ == "__main__":
    main()