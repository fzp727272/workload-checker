import requests
import json
import time
import os
import glob
import csv
from pathlib import Path
from typing import List, Dict, Optional, Any
from requests.exceptions import RequestException

def process_wiki_file(api_key: str, file_path: str, 
                     output_dir: str = "analyze",
                     relationship: str = "") -> Optional[str]:
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
        test_input = {
            "wiki": content,
            "relationship": relationship
        }
        
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
        response.raise_for_status()

        try:
            result = response.json()
        except json.JSONDecodeError:
            print("处理失败: 响应不是有效的JSON格式")
            print(f"错误信息: {response.text}")
            return None

        print(f"处理成功!")
        
        # 保存结果到文件并返回CSV路径
        csv_path = save_result_to_file(result, file_path, output_dir)
        
        return csv_path
            
    except RequestException as e:
        print(f"处理文件 {file_path} 时发生网络错误: {e}")
        return None
    except Exception as e:
        print(f"处理文件 {file_path} 时发生错误: {e}")
        return None
      
def save_result_to_file(result: Dict, original_file_path: str, output_dir: str) -> Optional[str]:
    """    
    将处理结果保存到文件，包括JSON和CSV格式
    
    Returns:
        生成的结果文件路径（优先返回CSV路径，否则返回JSON路径）
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
    
    # 2. 尝试从JSON中提取structured_output.data并保存为CSV
    try:
        data_node = result.get('data') if isinstance(result, dict) else None
        outputs_node = data_node.get('outputs') if isinstance(data_node, dict) else None
        structured_output = outputs_node.get('structured_output') if isinstance(outputs_node, dict) else None

        if structured_output is None:
            print("警告: 未找到 structured_output")
        else:
            # structured_output 可能是JSON字符串，先安全解析
            if isinstance(structured_output, str):
                try:
                    structured_output = json.loads(structured_output)
                except json.JSONDecodeError as e:
                    print(f"警告: structured_output 不是有效JSON字符串: {e}")
                    structured_output = None

            if isinstance(structured_output, dict) and isinstance(structured_output.get('data'), list):
                data_list = structured_output['data']

                normalized_rows = []
                for idx, row in enumerate(data_list, 1):
                    if isinstance(row, dict):
                        safe_row = {}
                        for k, v in row.items():
                            key = str(k)
                            if isinstance(v, (dict, list)):
                                safe_row[key] = json.dumps(v, ensure_ascii=False)
                            elif v is None:
                                safe_row[key] = ""
                            else:
                                safe_row[key] = v
                        normalized_rows.append(safe_row)
                    else:
                        print(f"警告: 第 {idx} 行不是字典格式，已跳过")

                if normalized_rows:
                    # 1. 收集所有出现的字段
                    all_fields = set()
                    for row in normalized_rows:
                        all_fields.update(row.keys())
                    fieldnames = sorted(list(all_fields))  # 排序使列顺序固定

                    # 2. 检查每行缺少的字段，并记录警告
                    missing_warnings = []
                    for idx, row in enumerate(normalized_rows):
                        row_fields = set(row.keys())
                        missing = all_fields - row_fields
                        if missing:
                            missing_warnings.append((idx, missing, row))

                    if missing_warnings:
                        print(f"警告: 发现 {len(missing_warnings)} 行存在缺失字段（已自动填充空值）:")
                        for idx, missing, row in missing_warnings:
                            print(f"  行 {idx+1}: 缺失字段 -> {sorted(missing)}")
                            print(f"      行内容预览: {str(row)[:200]}...")

                    # 3. 写入 CSV（所有行都保留）
                    csv_filename = f"{Path(original_file_path).stem}_result.csv"
                    csv_path = os.path.join(output_dir, csv_filename)
                    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as csvfile:
                        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
                        writer.writeheader()
                        writer.writerows(normalized_rows)

                    print(f"CSV结果已保存到: {csv_path}")
                    print(f"CSV包含 {len(normalized_rows)} 行数据，字段数: {len(fieldnames)}")
                else:
                    print("警告: structured_output.data 没有可用的字典行，不生成CSV文件")
            else:
                print("警告: 未找到 structured_output.data 或它不是列表格式")
    except (TypeError, ValueError) as e:
        print(f"警告: 解析 structured_output 时发生错误: {e}")
    except Exception as e:
        print(f"警告: 生成CSV文件时发生错误: {e}")
    
    # # 3. 同时保存一个简化的文本版本（保留原有功能）
    # text_output_path = os.path.join(output_dir, f"{original_filename}_result.txt")
    try:
        # 尝试提取工作流输出
        data_node = result.get('data') if isinstance(result, dict) else None
        outputs = data_node.get('outputs') if isinstance(data_node, dict) else None

        if isinstance(outputs, dict):
            text_output_path = os.path.join(output_dir, f"{original_filename}_result.txt")
            with open(text_output_path, 'w', encoding='utf-8-sig') as f:
                for key, value in outputs.items():
                    f.write(f"=== {key} ===\n")
                    if isinstance(value, dict) or isinstance(value, list):
                        f.write(f"{json.dumps(value, ensure_ascii=False, indent=2)}\n\n")
                    else:
                        f.write(f"{value}\n\n")
        else:
            # 如果没有outputs，保存整个结果的简化版本
            text_output_path = os.path.join(output_dir, f"{original_filename}_result.txt")
            with open(text_output_path, 'w', encoding='utf-8-sig') as f:
                f.write(f"处理时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"原始文件: {original_file_path}\n")
                f.write(f"结果概要: {json.dumps(result, ensure_ascii=False, indent=2)}\n")
    except Exception as e:
        print(f"警告: 保存文本版本时发生错误: {e}")
    
    # 返回CSV路径；若未生成CSV则返回JSON路径，确保调用方可识别处理成功
    return csv_path or json_path

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

def _normalize_mapping_key(value: str) -> str:
    """统一映射键格式，避免因大小写或空白差异导致匹配失败"""
    return value.strip().lower()


def load_relationship_mapping(mapping_file: str = "项目关系映射.csv") -> Dict[str, str]:
    """
    从CSV文件加载项目关系映射，支持键为文件名或不带扩展名的文件名
    CSV格式要求：第一列为文件名或标识，第二列为relationship
    """
    if not os.path.exists(mapping_file):
        print(f"警告: 未找到关系映射文件 '{mapping_file}'，relationship 将传入空值")
        return {}

    mapping: Dict[str, str] = {}
    try:
        with open(mapping_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            for idx, row in enumerate(reader, 1):
                if not row or len(row) < 2:
                    print(f"警告: 第{idx}行格式不正确，已跳过")
                    continue
                raw_key = str(row[0]).strip()
                value = "" if row[1] is None else str(row[1]).strip()
                if raw_key:
                    key_name = _normalize_mapping_key(raw_key)
                    key_stem = _normalize_mapping_key(Path(raw_key).stem)
                    mapping[key_name] = value
                    if key_stem:
                        mapping[key_stem] = value
    except Exception as e:
        print(f"警告: 读取关系映射CSV文件失败: {e}，relationship 将传入空值")
        return {}

    return mapping


def get_relationship_for_file(file_path: str, relationship_mapping: Dict[str, str]) -> str:
    """
    根据文件路径获取 relationship，优先匹配完整文件名，其次匹配不含扩展名
    """
    if not relationship_mapping:
        return ""

    file_name = _normalize_mapping_key(os.path.basename(file_path))
    file_stem = _normalize_mapping_key(Path(file_path).stem)
    return relationship_mapping.get(file_name, relationship_mapping.get(file_stem, ""))


def process_all_wiki_files(api_key: str, 
                          wiki_dir: str = "wiki", 
                          output_dir: str = "analyze",
                          delay_between_requests: float = 1.0,
                          relationship_mapping: Optional[Dict[str, str]] = None):
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
        current_mapping = relationship_mapping or {}
        relationship = get_relationship_for_file(file_path, current_mapping)
        if relationship:
            print(f"relationship: {relationship}")
        elif current_mapping:
            print(f"警告: 文件 '{os.path.basename(file_path)}' 未匹配到 relationship，将传入空值")

        result = process_wiki_file(api_key, file_path, output_dir, relationship=relationship)
        
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
    CONFIG_FILE = "config.json"  # API配置文件
    WIKI_DIR = "wiki"  # wiki文件夹名称
    OUTPUT_DIR = "analyze"  # 结果输出目录
    DELAY_BETWEEN_REQUESTS = 2.0  # 请求间隔时间（秒）
    RELATIONSHIP_MAPPING_FILE = "项目关系映射.json"  # 项目关系映射文件

    API_KEY = ""
    if not os.path.exists(CONFIG_FILE):
        print(f"错误: 未找到配置文件 '{CONFIG_FILE}'")
        print("请创建 config.json，例如: {\"api_key\": \"your-api-key\"}")
        return

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8-sig") as f:
            config_data: Any = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"错误: 读取配置文件失败: {e}")
        return

    if not isinstance(config_data, dict):
        print("错误: config.json 格式错误，应为JSON对象")
        return

    API_KEY = str(config_data.get("dify_api_key") or config_data.get("api_key") or "").strip()
    
    print("="*60)
    print("Dify Wiki文件批量处理器")
    print("="*60)
    if not API_KEY:
        print("错误: config.json 中未设置 dify_api_key 或 api_key")
        print("请在 config.json 中添加: {\"dify_api_key\": \"your-api-key\"} 或 {\"api_key\": \"your-api-key\"}")
        return
    print(f"API密钥: {API_KEY[:10]}...")  # 只显示前10个字符
    print(f"Wiki目录: {WIKI_DIR}")
    print(f"输出目录: {OUTPUT_DIR}")
    print(f"请求间隔: {DELAY_BETWEEN_REQUESTS} 秒")
    print(f"关系映射文件: {RELATIONSHIP_MAPPING_FILE}")
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
    
    # 加载关系映射
    relationship_mapping = load_relationship_mapping(RELATIONSHIP_MAPPING_FILE)
    print(f"已加载关系映射: {len(relationship_mapping)} 条")

    # 开始处理所有文件
    print("\n开始批量处理文件...")
    process_all_wiki_files(
        api_key=API_KEY,
        wiki_dir=WIKI_DIR,
        output_dir=OUTPUT_DIR,
        delay_between_requests=DELAY_BETWEEN_REQUESTS,
        relationship_mapping=relationship_mapping
    )

if __name__ == "__main__":
    main()