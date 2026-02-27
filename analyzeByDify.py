import requests
import json
import time
import os
import glob
import csv
from pathlib import Path
from typing import List, Dict, Optional

def process_wiki_file(api_key: str, file_path: str, 
                     output_dir: str = "analyze") -> Optional[str]:
    """
    处理单个wiki文件
    
    Returns:
        生成的CSV文件路径，如果处理失败则返回None
    """
    print(f"\n{'='*50}")
    print(f"处理文件: {file_path}")
    
    try:
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            content = f.read().strip()
        
        if not content:
            print(f"警告: 文件 {file_path} 为空，跳过")
            return None
            
        print(f"文件内容长度: {len(content)} 字符")
        
        # 创建输入数据
        test_input = {"wiki": content}
        
        # API端点
        url = "https://dify-api.pp.dktapp.cloud/v1/workflows/run"
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            "inputs": test_input,
            "response_mode": "blocking",
            "user": f"user-{Path(file_path).stem}"
        }
        
        # 发送请求
        print("发送请求到Dify工作流...")
        response = requests.post(url, headers=headers, json=data, timeout=300)
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"处理成功!")
            
            # 保存结果到文件并返回CSV路径
            csv_path = save_result_to_file(result, file_path, output_dir)
            
            return csv_path
        else:
            print(f"处理失败: {response.status_code}")
            print(f"错误信息: {response.text}")
            return None
            
    except Exception as e:
        print(f"处理文件 {file_path} 时发生错误: {e}")
        return None
      
def save_result_to_file(result: Dict, original_file_path: str, output_dir: str) -> Optional[str]:
    """
    将处理结果保存到文件，包括JSON和CSV格式
    要求：只输出13个固定字段并按顺序排列，其余字段丢弃
    
    Returns:
        生成的CSV文件路径，如果未生成则返回None
    """
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 获取原始文件名（不含扩展名）
    original_filename = Path(original_file_path).stem
    
    # 1. 保存JSON文件
    json_filename = f"{original_filename}_result.json"
    json_path = os.path.join(output_dir, json_filename)
    
    with open(json_path, 'w', encoding='utf-8-sig') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"JSON结果已保存到: {json_path}")
    
    csv_path = None  # 初始化CSV路径
    
    # 2. 从JSON中提取structured_output.data并生成CSV
    #    只保留13个指定字段，按顺序排列
    try:
        if ('data' in result and
            'outputs' in result['data'] and
            'structured_output' in result['data']['outputs']):

            structured_output = result['data']['outputs']['structured_output']
            if isinstance(structured_output, str):
                structured_output = json.loads(structured_output)

            if 'data' in structured_output and isinstance(structured_output['data'], list):
                data_list = structured_output['data']

                if data_list:
                    # 定义必须的13个字段及顺序
                    required_fields = [
                        "week_label",
                        "date_range",
                        "businessUnit",
                        "category",
                        "projectName",
                        "requirements",
                        "designer",
                        "po",
                        "task",
                        "task_status",
                        "task_time",
                        "time_horizon",
                        "detail"
                    ]

                    # 构造新的数据列表：每行只保留required_fields中的字段
                    filtered_data = []
                    missing_fields_count = 0
                    for idx, row in enumerate(data_list):
                        new_row = {}
                        for field in required_fields:
                            # 如果原始行包含该字段，取值；否则填充空字符串
                            value = row.get(field, "")
                            # 如果字段值是列表，转换为JSON字符串以便CSV存储
                            if isinstance(value, (list, dict)):
                                value = json.dumps(value, ensure_ascii=False)
                            new_row[field] = value
                        filtered_data.append(new_row)

                        # 统计缺失字段（可选，用于警告）
                        missing = [f for f in required_fields if f not in row]
                        if missing:
                            missing_fields_count += 1
                            if missing_fields_count <= 5:  # 只打印前5个警告
                                print(f"  行 {idx+1}: 缺失字段 -> {missing}")
                            elif missing_fields_count == 6:
                                print("  ... 更多缺失字段警告已省略")

                    if missing_fields_count > 0:
                        print(f"警告: 共有 {missing_fields_count} 行存在缺失字段，已自动填充空值")

                    # 写入CSV，字段顺序使用required_fields
                    csv_filename = f"{Path(original_file_path).stem}_result.csv"
                    csv_path = os.path.join(output_dir, csv_filename)
                    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as csvfile:
                        writer = csv.DictWriter(csvfile, fieldnames=required_fields)
                        writer.writeheader()
                        writer.writerows(filtered_data)

                    print(f"CSV结果已保存到: {csv_path}")
                    print(f"CSV包含 {len(filtered_data)} 行数据，字段数: {len(required_fields)}")
                    return csv_path
                else:
                    print("警告: structured_output.data 是空列表，不生成CSV文件")
            else:
                print("警告: 未找到 structured_output.data 或它不是列表格式")
    except Exception as e:
        print(f"警告: 生成CSV文件时发生错误: {e}")

    # 如果没有生成CSV，返回None
    return None
def get_wiki_files(wiki_dir: str = "wiki") -> List[str]:
    """
    获取wiki文件夹中的所有txt文件
    """
    # 确保wiki目录存在
    if not os.path.exists(wiki_dir):
        print(f"警告: wiki目录 '{wiki_dir}' 不存在，正在创建...")
        os.makedirs(wiki_dir, exist_ok=True)
        print(f"请在 '{wiki_dir}' 目录中添加txt文件后重新运行程序")
        return []
    
    # 获取所有txt文件
    txt_files = glob.glob(os.path.join(wiki_dir, "*.txt"))
    
    if not txt_files:
        print(f"警告: wiki目录 '{wiki_dir}' 中没有找到txt文件")
        print(f"支持的格式: *.txt")
        return []
    
    # 按文件名排序
    txt_files.sort()
    
    print(f"在 '{wiki_dir}' 目录中找到 {len(txt_files)} 个txt文件:")
    for i, file_path in enumerate(txt_files, 1):
        file_size = os.path.getsize(file_path)
        print(f"  {i}. {os.path.basename(file_path)} ({file_size} 字节)")
    
    return txt_files

def process_all_wiki_files(api_key: str, 
                          wiki_dir: str = "wiki", 
                          output_dir: str = "analyze",
                          delay_between_requests: float = 1.0):
    """
    处理wiki文件夹中的所有txt文件
    """
    # 获取所有txt文件
    txt_files = get_wiki_files(wiki_dir)

    
    if not txt_files:
        print("没有找到可处理的文件，程序退出")
        return
    
    print(f"\n开始处理 {len(txt_files)} 个文件...")
    print(f"请求间隔: {delay_between_requests} 秒")
    print(f"结果将保存到: {output_dir} 目录")
    
    success_count = 0
    fail_count = 0
    
    for i, file_path in enumerate(txt_files, 1):
        print(f"\n{'='*60}")
        print(f"处理进度: {i}/{len(txt_files)}")
        
        # 处理文件
        result = process_wiki_file(api_key, file_path, output_dir)
        
        if result:
            success_count += 1
        else:
            fail_count += 1
        
        # 如果不是最后一个文件，等待一段时间再处理下一个
        if i < len(txt_files):
            print(f"等待 {delay_between_requests} 秒后处理下一个文件...")
            time.sleep(delay_between_requests)
    
    print(f"\n{'='*60}")
    print("处理完成!")
    print(f"成功: {success_count} 个文件")
    print(f"失败: {fail_count} 个文件")
    print(f"结果保存在: {output_dir} 目录")

def main():
    """
    主函数
    """
    # 配置
    API_KEY = "app-QUvqZ01MPSa6t0wEOYbJk9YV"
    WIKI_DIR = "wiki"  # wiki文件夹名称
    OUTPUT_DIR = "analyze"  # 结果输出目录
    DELAY_BETWEEN_REQUESTS = 2.0  # 请求间隔时间（秒）
    
    print("="*60)
    print("Dify Wiki文件批量处理器")
    print("="*60)
    print(f"API密钥: {API_KEY[:10]}...")  # 只显示前10个字符
    print(f"Wiki目录: {WIKI_DIR}")
    print(f"输出目录: {OUTPUT_DIR}")
    print(f"请求间隔: {DELAY_BETWEEN_REQUESTS} 秒")
    print("="*60)
    
    # 显示wiki目录中的文件
    txt_files = get_wiki_files(WIKI_DIR)
    
    if not txt_files:
        print("没有找到可处理的文件。请将txt文件放入wiki文件夹后重新运行程序。")
        return
    
    # # 确认是否开始处理
    # print("\n" + "="*60)
    # user_input = input(f"找到 {len(txt_files)} 个文件，是否开始处理? (y/n): ").strip().lower()
    
    # if user_input not in ['y', 'yes', '是']:
    #     print("用户取消操作")
    #     return
    
    # 开始处理所有文件
    print("\n开始批量处理文件...")
    process_all_wiki_files(
        api_key=API_KEY,
        wiki_dir=WIKI_DIR,
        output_dir=OUTPUT_DIR,
        delay_between_requests=DELAY_BETWEEN_REQUESTS
    )

if __name__ == "__main__":
    main()