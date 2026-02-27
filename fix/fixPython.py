#!/usr/bin/env python3
"""
修复Python环境问题脚本
这个脚本会检测并修复常见的Python环境问题
"""

import os
import sys
import subprocess
import platform
import json
from pathlib import Path

def check_python_version():
    """检查Python版本"""
    print("="*60)
    print("检查Python环境")
    print("="*60)
    
    python_version = sys.version_info
    print(f"Python版本: {sys.version}")
    print(f"主版本: {python_version.major}")
    print(f"次版本: {python_version.minor}")
    print(f"微版本: {python_version.micro}")
    
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 7):
        print(f"⚠ 警告: Python版本 {python_version.major}.{python_version.minor} 可能太低")
        print("建议使用 Python 3.7 或更高版本")
        return False
    else:
        print("✓ Python版本符合要求")
        return True

def check_pip():
    """检查pip是否可用"""
    print("\n检查pip...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "--version"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"✓ pip可用: {result.stdout.strip()}")
            return True
        else:
            print(f"✗ pip检查失败: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ pip检查异常: {e}")
        return False

def fix_pip_issues():
    """尝试修复pip问题"""
    print("\n尝试修复pip问题...")
    
    # 升级pip
    print("1. 升级pip...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
            check=True
        )
        print("✓ pip升级成功")
    except subprocess.CalledProcessError as e:
        print(f"⚠ pip升级失败: {e}")
    
    # 尝试使用pip的旧版本格式
    print("\n2. 尝试使用--use-deprecated=legacy-resolver...")
    try:
        subprocess.run(
            [
                sys.executable, "-m", "pip", "install", 
                "--use-deprecated=legacy-resolver",
                "pip"
            ],
            check=True
        )
        print("✓ 使用legacy-resolver成功")
    except Exception as e:
        print(f"⚠ 使用legacy-resolver失败: {e}")
    
    return True

def install_dependencies_safely():
    """安全安装依赖"""
    print("\n" + "="*60)
    print("安装项目依赖")
    print("="*60)
    
    # 要安装的包（使用兼容版本）
    packages = [
        "Flask==2.3.3",
        "requests==2.31.0",
        "pandas==1.5.3",  # 使用旧版本避免兼容性问题
        "beautifulsoup4==4.12.2",
        "lxml==4.9.3",
        "openpyxl==3.1.2",  # pandas可能需要这个来读写Excel
    ]
    
    success_count = 0
    fail_count = 0
    
    # 逐个安装，避免一个失败影响全部
    for package in packages:
        print(f"\n安装 {package}...")
        try:
            # 使用多个来源和选项
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

def create_venv():
    """创建虚拟环境"""
    print("\n" + "="*60)
    print("创建Python虚拟环境")
    print("="*60)
    
    venv_dir = "venv"
    
    if os.path.exists(venv_dir):
        print(f"✓ 虚拟环境已存在: {venv_dir}")
        return True
    
    print(f"创建虚拟环境到 {venv_dir}...")
    try:
        subprocess.run([sys.executable, "-m", "venv", venv_dir], check=True)
        print("✓ 虚拟环境创建成功")
        
        # 根据操作系统确定激活路径
        system = platform.system()
        if system == "Windows":
            python_path = os.path.join(venv_dir, "Scripts", "python.exe")
            pip_path = os.path.join(venv_dir, "Scripts", "pip.exe")
        else:
            python_path = os.path.join(venv_dir, "bin", "python")
            pip_path = os.path.join(venv_dir, "bin", "pip")
        
        print(f"虚拟环境Python路径: {python_path}")
        print(f"虚拟环境pip路径: {pip_path}")
        
        return True
    except Exception as e:
        print(f"✗ 创建虚拟环境失败: {e}")
        return False

def check_imports():
    """检查所有必需的导入"""
    print("\n" + "="*60)
    print("检查Python包导入")
    print("="*60)
    
    modules_to_check = [
        "flask",
        "requests",
        "pandas",
        "bs4",  # beautifulsoup4
        "lxml",
        "csv",
        "json",
        "os",
        "sys",
    ]
    
    all_ok = True
    for module in modules_to_check:
        try:
            __import__(module)
            print(f"✓ {module} 导入成功")
        except ImportError as e:
            print(f"✗ {module} 导入失败: {e}")
            all_ok = False
    
    return all_ok

def create_minimal_app():
    """创建最小化的应用"""
    print("\n" + "="*60)
    print("创建最小化应用")
    print("="*60)
    
    app_content = '''#!/usr/bin/env python3
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
            f.write(f"报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n")
            f.write("="*50 + "\\n")
            f.write("设计工时汇总\\n")
            f.write("="*50 + "\\n")
            f.write("总设计师: 4人\\n")
            f.write("总项目数: 4个\\n")
            f.write("总工时: 150小时\\n")
            f.write("平均工时: 37.5小时/人\\n")
        
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
        
        print("\\n" + "="*60)
        print("完成!")
        print(f"CSV文件: {csv_path}")
        print(f"摘要文件: {summary_path}")
        print("="*60)

if __name__ == "__main__":
    generator = SimpleReportGenerator()
    generator.run()
'''
    
    app_file = Path("simple_report_generator.py")
    with open(app_file, 'w', encoding='utf-8-sig') as f:
        f.write(app_content)
    
    # 设置为可执行（Unix-like系统）
    if platform.system() != "Windows":
        os.chmod(app_file, 0o755)
    
    print(f"✓ 已创建最小化应用: {app_file}")
    return True

def create_requirements_txt():
    """创建requirements.txt文件"""
    print("\n创建requirements.txt文件...")
    
    requirements = """# Wiki报告生成器依赖
# 基本依赖
Flask==2.3.3
requests==2.31.0

# 数据处理
pandas==1.5.3
numpy==1.24.3

# 网页解析
beautifulsoup4==4.12.2
lxml==4.9.3

# Excel支持（可选）
openpyxl==3.1.2
xlrd==2.0.1

# 开发工具（可选）
python-dotenv==1.0.0
"""
    
    with open("requirements.txt", "w", encoding="utf-8") as f:
        f.write(requirements)
    
    print("✓ requirements.txt 已创建")

def create_launcher_scripts():
    """创建启动脚本"""
    print("\n" + "="*60)
    print("创建启动脚本")
    print("="*60)
    
    # Windows批处理文件
    windows_bat = '''@echo off
echo ========================================
echo Wiki报告生成器 - Windows启动器
echo ========================================

REM 检查Python
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo 错误: Python未找到
    echo 请安装Python 3.7或更高版本
    pause
    exit /b 1
)

REM 检查Python版本
python --version

REM 安装依赖（如果需要）
echo.
echo 正在检查依赖...
python -c "import flask, requests, pandas" 2>nul
if %ERRORLEVEL% neq 0 (
    echo 正在安装依赖...
    python -m pip install -r requirements.txt --user
)

REM 运行应用
echo.
echo 启动报告生成器...
python simple_report_generator.py

pause
'''
    
    with open("launch_windows.bat", "w", encoding="utf-8") as f:
        f.write(windows_bat)
    
    # Unix shell脚本
    unix_sh = '''#!/bin/bash
echo "========================================"
echo "Wiki报告生成器 - Linux/Mac启动器"
echo "========================================"

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "错误: Python3未找到"
    echo "请安装Python 3.7或更高版本"
    exit 1
fi

# 检查Python版本
python3 --version

# 检查依赖
echo ""
echo "检查依赖..."
python3 -c "import flask, requests, pandas" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "安装依赖..."
    pip3 install -r requirements.txt --user
fi

# 运行应用
echo ""
echo "启动报告生成器..."
python3 simple_report_generator.py
'''
    
    with open("launch_unix.sh", "w", encoding="utf-8") as f:
        f.write(unix_sh)
    
    # 设置为可执行
    if platform.system() != "Windows":
        os.chmod("launch_unix.sh", 0o755)
    
    print("✓ Windows启动器: launch_windows.bat")
    print("✓ Unix启动器: launch_unix.sh")

def create_directories():
    """创建必要的目录"""
    print("\n创建必要的目录...")
    
    directories = [
        "wiki",
        "analyze", 
        "result",
        "simple_results",
        "data"
    ]
    
    for dir_name in directories:
        Path(dir_name).mkdir(exist_ok=True)
        print(f"✓ 创建目录: {dir_name}")

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

def main():
    """主函数"""
    print("="*60)
    print("Wiki报告生成器 - 环境修复工具")
    print("="*60)
    
    # 检查Python版本
    if not check_python_version():
        print("\n⚠ 建议升级Python到3.7或更高版本")
        print("下载地址: https://www.python.org/downloads/")
    
    # 检查pip
    if not check_pip():
        print("\n尝试修复pip...")
        fix_pip_issues()
    
    # 创建目录
    create_directories()
    
    # 创建最小化应用
    create_minimal_app()
    
    # 创建requirements.txt
    create_requirements_txt()
    
    # 创建启动脚本
    create_launcher_scripts()
    
    # 生成诊断报告
    generate_diagnostic_report()
    
    # 尝试安装依赖
    print("\n" + "="*60)
    print("是否安装完整依赖?")
    print("输入 'y' 安装，输入 'n' 跳过")
    print("="*60)
    
    choice = input("选择 (y/n): ").strip().lower()
    if choice == 'y':
        install_dependencies_safely()
    
    # 检查导入
    print("\n" + "="*60)
    print("检查Python包导入状态")
    print("="*60)
    check_imports()
    
    # 创建虚拟环境（可选）
    print("\n" + "="*60)
    print("是否创建Python虚拟环境?")
    print("虚拟环境可以避免包冲突")
    print("="*60)
    
    choice = input("创建虚拟环境? (y/n): ").strip().lower()
    if choice == 'y':
        create_venv()
    
    print("\n" + "="*60)
    print("修复完成!")
    print("="*60)
    print("下一步:")
    print("1. 运行最小化应用: python simple_report_generator.py")
    print("2. 或使用启动脚本:")
    print("   - Windows: 双击 launch_windows.bat")
    print("   - Mac/Linux: 运行 ./launch_unix.sh")
    print("3. 查看诊断报告: diagnostic_report.json")
    print("="*60)
    
    # 询问是否立即运行
    choice = input("\n是否立即运行最小化应用? (y/n): ").strip().lower()
    if choice == 'y':
        print("\n运行应用...")
        subprocess.run([sys.executable, "simple_report_generator.py"])

if __name__ == "__main__":
    main()