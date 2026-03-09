import pandas as pd
import os
import glob
import re
import json
from datetime import datetime
from typing import List, Dict, Any

def load_config(config_path: str = "config.json") -> Dict[str, Any]:
    """从config.json加载配置"""
    try:
        with open(config_path, 'r', encoding='utf-8-sig') as f:
            config = json.load(f)
        print(f"成功加载配置文件: {config_path}")
        return config
    except FileNotFoundError:
        print(f"配置文件 {config_path} 不存在，使用默认配置")
        return {
            "base_url": "https://decathlon.atlassian.net/wiki",
            "username": "",
            "api_token": "",
            "dify_api_key": "",
            "page_ids": [],
            "max_retries": 2,
            "clean_files": False
        }
    except json.JSONDecodeError as e:
        print(f"配置文件格式错误: {e}，使用默认配置")
        return {
            "base_url": "https://decathlon.atlassian.net/wiki",
            "username": "",
            "api_token": "",
            "dify_api_key": "",
            "page_ids": [],
            "max_retries": 2,
            "clean_files": False
        }

def find_csv_by_page_id(page_ids: List[str], analyze_dir: str = "analyze") -> List[str]:
    """根据page_id在analyze目录中查找对应的CSV文件"""
    csv_files = []
    
    # 确保analyze目录存在
    if not os.path.exists(analyze_dir):
        print(f"警告: analyze目录 '{analyze_dir}' 不存在，正在创建...")
        os.makedirs(analyze_dir, exist_ok=True)
        print(f"请在 '{analyze_dir}' 目录中添加CSV文件后重新运行程序")
        return []
    
    if not page_ids:
        print("警告: 配置中没有page_ids，无法查找对应的CSV文件")
        return []
    
    # 获取analyze目录中的所有CSV文件
    all_csv_files = glob.glob(os.path.join(analyze_dir, "*.csv"))
    
    if not all_csv_files:
        print(f"警告: analyze目录 '{analyze_dir}' 中没有找到CSV文件")
        print(f"支持的格式: *.csv")
        return []
    
    print(f"在 '{analyze_dir}' 目录中找到 {len(all_csv_files)} 个CSV文件:")
    for i, file_path in enumerate(all_csv_files, 1):
        file_size = os.path.getsize(file_path)
        print(f"  {i}. {os.path.basename(file_path)} ({file_size} 字节)")
    
    # 根据page_id查找对应的CSV文件
    for page_id in page_ids:
        # 查找文件名中包含page_id的CSV文件
        matching_files = [f for f in all_csv_files if page_id in os.path.basename(f)]
        
        if matching_files:
            # 如果有多个匹配，选择最新的（按修改时间排序）
            if len(matching_files) > 1:
                print(f"找到 {len(matching_files)} 个包含page_id '{page_id}' 的CSV文件:")
                for mf in matching_files:
                    print(f"  - {os.path.basename(mf)}")
                
                # 按修改时间排序，选择最新的
                matching_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                print(f"选择最新的文件: {os.path.basename(matching_files[0])}")
            
            csv_files.extend(matching_files)
        else:
            print(f"警告: 未找到包含page_id '{page_id}' 的CSV文件")
    
    # 去重
    csv_files = list(set(csv_files))
    
    if csv_files:
        print(f"根据page_id找到 {len(csv_files)} 个CSV文件:")
        for i, file_path in enumerate(csv_files, 1):
            print(f"  {i}. {os.path.basename(file_path)}")
    else:
        print("错误: 根据page_id未找到任何CSV文件")
    
    return csv_files

def read_csv_files(file_paths: List[str]) -> pd.DataFrame:
    """读取多个CSV文件并合并为一个DataFrame"""
    all_data = []
    
    for file_path in file_paths:
        try:
            df = pd.read_csv(file_path)
            all_data.append(df)
            print(f"成功读取文件: {file_path}")
        except Exception as e:
            print(f"读取文件 {file_path} 时出错: {e}")
    
    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        return combined_df
    else:
        return pd.DataFrame()

def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """数据清洗和处理，兼容新数据格式"""
    cleaned_df = df.copy()

    # 字段映射：新数据格式 -> 旧代码字段
    column_map = {
        'requirement_time': 'task_time',
        'BU': 'businessUnit',
        'category': 'category',
        'designer': 'designer',
        'requirement_status': 'task_status',
        'week_label': 'week_label',
        'date_range': 'date_range',
        'time_horizon': 'time_horizon',
    }

    # 兼容新表格格式，直接重命名字段
    for src, dst in column_map.items():
        if src in cleaned_df.columns:
            cleaned_df[dst] = cleaned_df[src]

    # requirement 字段同时用于项目名称与任务名称
    if 'requirement' in cleaned_df.columns:
        cleaned_df['projectName'] = cleaned_df['requirement']
        cleaned_df['task'] = cleaned_df['requirement']
    elif 'projectName' in cleaned_df.columns:
        cleaned_df['requirement'] = cleaned_df['projectName']
        cleaned_df['task'] = cleaned_df['projectName']
    else:
        cleaned_df['requirement'] = None
        cleaned_df['projectName'] = None
        cleaned_df['task'] = None

    # 确保所有需要的列都存在
    required_columns = [
        'task_time', 'businessUnit', 'category', 'projectName', 'requirement',
        'designer', 'task_status', 'week_label', 'date_range', 'task', 'time_horizon'
    ]
    for col in required_columns:
        if col not in cleaned_df.columns:
            if col == 'task_time':
                cleaned_df[col] = 0
            else:
                cleaned_df[col] = None

    # 处理工时数据：转换为数值类型
    def parse_task_time(time_val):
        if pd.isna(time_val):
            return 0
        try:
            if isinstance(time_val, str):
                numbers = re.findall(r'\d+\.?\d*', str(time_val))
                if numbers:
                    return float(numbers[0])
                else:
                    return 0
            return float(time_val)
        except:
            return 0

    cleaned_df['task_time'] = cleaned_df['task_time'].apply(parse_task_time)

    # 填充空值
    cleaned_df['businessUnit'] = cleaned_df['businessUnit'].fillna('未分类')
    cleaned_df['category'] = cleaned_df['category'].fillna('未分类')
    cleaned_df['projectName'] = cleaned_df['projectName'].fillna('未命名项目')
    cleaned_df['requirement'] = cleaned_df['requirement'].fillna('未命名需求')
    cleaned_df['designer'] = cleaned_df['designer'].fillna('未知设计师')
    cleaned_df['task_status'] = cleaned_df['task_status'].fillna('未记录')
    cleaned_df['week_label'] = cleaned_df['week_label'].fillna('未知周期')
    cleaned_df['date_range'] = cleaned_df['date_range'].fillna('未知日期')
    cleaned_df['task'] = cleaned_df['task'].fillna('未知任务')
    cleaned_df['time_horizon'] = cleaned_df['time_horizon'].fillna('未知周期')

    return cleaned_df

def generate_designer_summary(df: pd.DataFrame) -> Dict[str, Any]:
    """生成设计师工时汇总"""
    designer_summary = {}
    
    for designer in df['designer'].unique():
        if pd.isna(designer) or designer == '未知设计师':
            continue
            
        designer_tasks = df[df['designer'] == designer]
        total_hours = designer_tasks['task_time'].sum()
        
        # 获取需求列表（过滤NaN值）
        requirement_list = designer_tasks['requirement'].dropna().unique().tolist()
        requirement_count = len(requirement_list)
        
        # 确保需求名称都是字符串
        requirement_list = [str(p) for p in requirement_list]
        
        designer_summary[designer] = {
            'total_hours': total_hours,
            'project_count': requirement_count,
            'projects': requirement_list
        }
    
    return designer_summary

def generate_project_summary(df: pd.DataFrame) -> Dict[str, Any]:
    """生成需求工时分布"""
    project_summary = {}
    
    for requirement in df['requirement'].unique():
        if pd.isna(requirement) or requirement == '未命名需求':
            continue
            
        requirement_tasks = df[df['requirement'] == requirement]
        total_hours = requirement_tasks['task_time'].sum()
        
        # 获取需求相关信息
        if not requirement_tasks.empty:
            category = requirement_tasks['category'].iloc[0] if 'category' in requirement_tasks.columns else '未分类'
            business_unit = requirement_tasks['businessUnit'].iloc[0] if 'businessUnit' in requirement_tasks.columns else '未分类'
            
            # 获取设计师列表（过滤NaN值）
            designers = requirement_tasks['designer'].dropna().unique().tolist()
            designers = [str(d) for d in designers if d != '未知设计师']
            
            # 获取状态列表（过滤NaN值）
            statuses = requirement_tasks['task_status'].dropna().unique().tolist()
            statuses = [str(s) for s in statuses]
            
            project_summary[requirement] = {
                'total_hours': total_hours,
                'category': category,
                'business_unit': business_unit,
                'designers': designers,
                'statuses': statuses
            }
    
    return project_summary

def generate_department_summary(df: pd.DataFrame) -> Dict[str, Any]:
    """生成业务部门工作分布"""
    department_summary = {}
    
    for dept in df['businessUnit'].unique():
        if pd.isna(dept) or dept == '未分类':
            continue
            
        dept_tasks = df[df['businessUnit'] == dept]
        total_hours = dept_tasks['task_time'].sum()
        
        # 获取需求列表（过滤NaN值）
        requirements = dept_tasks['requirement'].dropna().unique().tolist()
        requirement_count = len(requirements)
        
        # 确保需求名称都是字符串
        requirements = [str(p) for p in requirements]
        
        department_summary[dept] = {
            'total_hours': total_hours,
            'project_count': requirement_count,
            'projects': requirements
        }
    
    return department_summary

def generate_week_summary(df: pd.DataFrame) -> Dict[str, Any]:
    """生成本周与下周工作对比"""
    week_summary = {
        'current_week': [],
        'next_week': []
    }
    
    # 获取week_label（周期信息），用于markdown报告
    week_label = None
    if 'week_label' in df.columns and not df['week_label'].isna().all():
        week_label = df['week_label'].dropna().iloc[0]
    else:
        week_label = "未知周期"
    week_summary['week_label'] = week_label

    # 分离本周和下周工作
    if 'time_horizon' in df.columns:
        current_week_tasks = df[df['time_horizon'] == '本周工作']
        next_week_tasks = df[df['time_horizon'] == '下周工作']
        
        for _, task in current_week_tasks.iterrows():
            week_summary['current_week'].append({
                'project': task.get('requirement', '未知需求'),
                'task': task.get('task', '未知任务'),
                'designer': task.get('designer', '未知设计师'),
                'hours': task.get('task_time', 0),
                'status': task.get('task_status', '未记录'),
                'week_label': task.get('week_label', week_label)
            })
        
        for _, task in next_week_tasks.iterrows():
            week_summary['next_week'].append({
                'project': task.get('requirement', '未知需求'),
                'task': task.get('task', '未知任务'),
                'designer': task.get('designer', '未知设计师'),
                'hours': task.get('task_time', 0),
                'week_label': task.get('week_label', week_label)
            })
    
    return week_summary

def generate_insights(df: pd.DataFrame) -> List[str]:
    """生成关键发现与建议"""
    insights = []
    
    # 检查工时记录完整性
    missing_hours_count = df['task_time'].isna().sum() + (df['task_time'] == 0).sum()
    total_tasks = len(df)
    missing_percentage = (missing_hours_count / total_tasks) * 100 if total_tasks > 0 else 0
    
    if missing_percentage > 30:
        insights.append(f"工时记录不完整：{missing_percentage:.1f}%的任务未记录工时，建议统一填写规范。")
    elif missing_percentage > 0:
        insights.append(f"工时记录需完善：{missing_percentage:.1f}%的任务未记录工时。")
    
    # 检查设计师工作负载
    designer_hours = df.groupby('designer')['task_time'].sum()
    if not designer_hours.empty:
        max_hours_designer = designer_hours.idxmax()
        max_hours = designer_hours.max()
        min_hours_designer = designer_hours.idxmin()
        min_hours = designer_hours.min()
        
        if max_hours > 0:
            insights.append(f"工时投入最高：{max_hours_designer} 投入{max_hours}h，显示为重点项目负责人。")
        
        if min_hours == 0 and max_hours > 0:
            insights.append(f"工时分配不均：{min_hours_designer} 未记录工时，{max_hours_designer} 投入最多。")
    
    # 检查项目状态分布
    status_counts = df['task_status'].value_counts()
    if '进行中' in status_counts.index:
        ongoing_count = status_counts['进行中']
        insights.append(f"进行中任务：共有{ongoing_count}个任务状态为'进行中'，建议关注进度与风险。")
    
    # 检查业务部门分布
    dept_counts = df['businessUnit'].value_counts()
    if len(dept_counts) > 0:
        top_dept = dept_counts.index[0]
        insights.append(f"业务部门分布：{top_dept}部门任务最多，共{dept_counts.iloc[0]}个任务。")
    
    # 检查本周/下周任务分布
    if 'time_horizon' in df.columns:
        time_horizon_counts = df['time_horizon'].value_counts()
        current_week_count = time_horizon_counts.get('本周工作', 0)
        next_week_count = time_horizon_counts.get('下周工作', 0)
        
        if current_week_count > 0 and next_week_count > 0:
            insights.append(f"任务规划：本周任务{current_week_count}项，下周计划{next_week_count}项，规划清晰。")
    
    return insights

def generate_markdown_report(
    designer_summary: Dict[str, Any],
    project_summary: Dict[str, Any],
    department_summary: Dict[str, Any],
    week_summary: Dict[str, Any],
    insights: List[str],
    source_files: List[str],
    page_ids: List[str]
) -> str:
    """生成Markdown格式报告"""
    
    current_date = datetime.now().strftime("%Y-%m-%d")
    week_label = week_summary.get('week_label', "未知周期")
    
    markdown = f"""# 设计师工时与项目分析报告  
**周期**：{week_label}  
**生成日期**：{current_date}  
**数据来源page_id**：{', '.join(page_ids) if page_ids else '未指定'}  
**CSV文件**：{', '.join([os.path.basename(f) for f in source_files]) if source_files else '无'}  

---

## 一、设计师工时汇总

| 设计师 | 本周总工时（h） | 涉及项目数量 | 项目列表 |
|--------|----------------|--------------|----------|
"""
    
    # 添加设计师汇总表
    for designer, data in designer_summary.items():
        # 确保项目列表中的元素都是字符串
        projects = data.get('projects', [])
        if projects:
            projects = [str(p) for p in projects if pd.notna(p) and str(p).strip() != '']
            projects_str = ', '.join(projects[:3])  # 只显示前3个项目
            if len(projects) > 3:
                projects_str += f" 等{len(projects)}个项目"
        else:
            projects_str = "无项目"
        
        markdown += f"| {designer} | {data['total_hours']} | {data['project_count']} | {projects_str} |\n"
    
    markdown += f"""
> 注：部分任务未记录工时，表中显示为0h。

---

## 二、需求工时分布

| 需求类别 | 需求名称 | 总工时（h） | 设计师 | 状态 |
|----------|----------|------------|--------|------|
"""
    
    # 添加项目汇总表
    for project, data in project_summary.items():
        if data['total_hours'] > 0 or data['statuses']:
            # 确保设计师列表中的元素都是字符串
            designers = data.get('designers', [])
            designers = [str(d) for d in designers if pd.notna(d) and str(d).strip() != '']
            designers_str = ', '.join(designers) if designers else "未知设计师"
            
            # 确保状态列表中的元素都是字符串
            statuses = data.get('statuses', [])
            statuses = [str(s) for s in statuses if pd.notna(s) and str(s).strip() != '']
            statuses_str = ', '.join(statuses[:2]) if statuses else "未记录"  # 只显示前2个状态
            if len(statuses) > 2:
                statuses_str += "等"
            
            markdown += f"| {data['category']} | {project} | {data['total_hours']} | {designers_str} | {statuses_str} |\n"
    
    markdown += """
---

## 三、业务部门工作分布

| 业务部门 | 需求数量 | 总工时（h） | 主要需求 |
|----------|----------|------------|----------|
"""
    
    # 添加部门汇总表
    for dept, data in department_summary.items():
        # 确保项目列表中的元素都是字符串
        projects = data.get('projects', [])
        if projects:
            projects = [str(p) for p in projects if pd.notna(p) and str(p).strip() != '']
            projects_str = ', '.join(projects[:2])  # 只显示前2个项目
            if len(projects) > 2:
                projects_str += f" 等{len(projects)}个项目"
        else:
            projects_str = "无项目"
        
        markdown += f"| {dept} | {data['project_count']} | {data['total_hours']} | {projects_str} |\n"
    
    markdown += """
---

## 四、本周 vs 下周工作对比

### ✅ 本周已完成/进行中任务：
"""
    
    # 添加本周工作
    if week_summary['current_week']:
        for task in week_summary['current_week']:
            hours_info = f"，工时：{task['hours']}h" if task['hours'] > 0 else ""
            markdown += f"- {task['project']} - {task['task']}（{task['designer']}{hours_info}，状态：{task['status']}）\n"
    else:
        markdown += "无本周工作记录\n"
    
    markdown += """
### 📅 下周计划任务：
"""
    
    # 添加下周工作
    if week_summary['next_week']:
        for task in week_summary['next_week']:
            hours_info = f"，计划工时：{task['hours']}h" if task['hours'] > 0 else ""
            markdown += f"- {task['project']} - {task['task']}（{task['designer']}{hours_info}）\n"
    else:
        markdown += "无下周工作计划\n"
    
    markdown += """
---

## 五、关键发现与建议
"""
    
    # 添加关键发现
    if insights:
        for i, insight in enumerate(insights, 1):
            markdown += f"{i}. {insight}\n"
    else:
        markdown += "暂无关键发现。\n"
    
    markdown += f"""
---

## 六、数据说明

- 本报告基于CSV文件数据自动生成
- 数据来源page_id: {', '.join(page_ids) if page_ids else '未指定'}
- 工时数据可能不完整，部分任务未记录具体工时
- 建议后续补充任务优先级、依赖关系等信息
- 报告生成时间：{current_date}

**保存位置**：`result/设计师工时与项目分析报告.md`
"""
    
    return markdown

def save_report(markdown_content: str, output_dir: str = "result"):
    """保存Markdown报告到文件"""
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 生成文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"设计师工时与项目分析报告_{timestamp}.md"
    filepath = os.path.join(output_dir, filename)
    
    # 保存文件
    with open(filepath, 'w', encoding='utf-8-sig') as f:
        f.write(markdown_content)
    
    print(f"报告已保存到: {filepath}")
    return filepath


def main(csv_files=None):
    """主函数"""
    
    # 加载配置
    config = load_config()
    print(f"配置信息: base_url={config.get('base_url')}, username={config.get('username')}")
    print(f"页面ID列表: {config.get('page_ids')}")
    print(f"最大重试次数: {config.get('max_retries')}")
    print(f"清理文件: {config.get('clean_files')}")
    
    # 获取page_ids
    page_ids = config.get('page_ids', [])
    
    # 根据page_id查找CSV文件
    if csv_files is None and page_ids:
        csv_files = find_csv_by_page_id(page_ids, "analyze")
    
    # 如果未找到文件，则分析analyze目录下所有CSV文件
    if not csv_files:
        csv_files = glob.glob(os.path.join("analyze", "*.csv"))
    
    if not csv_files:
        print("未找到CSV文件")
        return
    
    print(f"开始处理 {len(csv_files)} 个CSV文件...")
    
    # 读取数据
    df = read_csv_files(csv_files)
    
    if df.empty:
        print("数据读取失败或文件为空")
        return
    
    print(f"成功读取 {len(df)} 行数据")
    
    # 数据清洗
    df = clean_data(df)
    
    # 生成各类汇总
    designer_summary = generate_designer_summary(df)
    project_summary = generate_project_summary(df)
    department_summary = generate_department_summary(df)
    week_summary = generate_week_summary(df)
    insights = generate_insights(df)
    
    # 生成Markdown报告
    markdown_report = generate_markdown_report(
        designer_summary, project_summary, department_summary, 
        week_summary, insights, csv_files, page_ids
    )
    
    # 保存报告
    save_report(markdown_report)
    
    print("报告生成完成！")
    
    
    

if __name__ == "__main__":
    main()