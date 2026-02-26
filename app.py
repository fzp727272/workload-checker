import os
import json
import uuid
import subprocess
import threading
import sys
from flask import Flask, request, render_template, jsonify, send_from_directory
import time

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # 用于 session，生产环境请使用随机字符串

# 全局任务状态存储
tasks = {}
tasks_lock = threading.Lock()

def load_config():
    with open('config.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def save_config(config):
    with open('config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def run_report_task(task_id, page_ids):
    # 辅助函数：获取目录中指定扩展名文件的 {文件名: 修改时间戳}
    def get_files_mtime(directory, ext):
        if not os.path.exists(directory):
            return {}
        files = {}
        for f in os.listdir(directory):
            if f.lower().endswith(ext):
                path = os.path.join(directory, f)
                files[f] = os.path.getmtime(path)
        return files

    # 1. 记录任务开始前的文件及其修改时间
    old_md = get_files_mtime('result', '.md')
    old_csv = get_files_mtime('analyze', '.csv')

    # 2. 更新配置并启动子进程
    config = load_config()
    config['page_ids'] = page_ids
    save_config(config)

    cmd = [sys.executable, 'run_report.py']
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1
    )

    logs = []
    for line in process.stdout:
        logs.append(line.rstrip())
        print(line, end='')

    process.wait()

    # 3. 任务结束后再次扫描
    new_md = get_files_mtime('result', '.md')
    new_csv = get_files_mtime('analyze', '.csv')

    # 4. 判断新增或更新的文件（修改时间变大）
    added_md = []
    for f, mtime in new_md.items():
        if f not in old_md or old_md[f] < mtime:
            added_md.append(f)

    added_csv = []
    for f, mtime in new_csv.items():
        if f not in old_csv or old_csv[f] < mtime:
            added_csv.append(f)

    # 5. 更新任务状态
    with tasks_lock:
        tasks[task_id]['logs'] = logs
        if process.returncode == 0:
            tasks[task_id]['status'] = 'completed'
            tasks[task_id]['result'] = added_md
            tasks[task_id]['csv_files'] = added_csv
        else:
            tasks[task_id]['status'] = 'failed'
            tasks[task_id]['error'] = f'进程退出码 {process.returncode}'

@app.route('/')
def index():
    config = load_config()
    page_ids_str = '\n'.join(config.get('page_ids', []))
    return render_template('index.html', page_ids=page_ids_str)

@app.route('/run', methods=['POST'])
def run():
    page_ids_text = request.form.get('page_ids', '')
    page_ids = [pid.strip() for pid in page_ids_text.splitlines() if pid.strip()]
    if not page_ids:
        return jsonify({'error': '至少提供一个页面 ID'}), 400

    # 更新配置文件中的 page_ids
    config = load_config()
    config['page_ids'] = page_ids
    save_config(config)

    # 生成任务 ID
    task_id = str(uuid.uuid4())
    with tasks_lock:
        tasks[task_id] = {
            'status': 'running',
            'logs': [],
            'result': None,
            'csv_files': None,   # 新增 CSV 文件列表字段
            'error': None
        }

    # 启动后台线程
    thread = threading.Thread(target=run_report_task, args=(task_id, page_ids))
    thread.daemon = True
    thread.start()

    return jsonify({'task_id': task_id})

@app.route('/logs/<task_id>')
def get_logs(task_id):
    with tasks_lock:
        task = tasks.get(task_id)
        if not task:
            return jsonify({'error': '任务不存在'}), 404
        return jsonify({
            'status': task['status'],
            'logs': task['logs'],
            'result': task['result'],
            'csv_files': task.get('csv_files', []),   # 返回 CSV 文件列表
            'error': task.get('error')
        })

@app.route('/result/<path:filename>')
def download_report(filename):
    """提供报告文件下载"""
    return send_from_directory('result', filename)

@app.route('/analyze/<filename>')
def get_csv(filename):
    return send_from_directory('analyze', filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, threaded=True, port=5000)  # port 可省略，默认5000