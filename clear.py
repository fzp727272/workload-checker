import os

def clean_folders(folders: list):
    """
    清空指定文件夹下的所有文件（不删除文件夹本身，不递归子文件夹）。
    """
    for folder in folders:
        if os.path.exists(folder):
            for filename in os.listdir(folder):
                file_path = os.path.join(folder, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
                elif os.path.isdir(file_path):
                    # 如需连子文件夹内容一并清空可用：shutil.rmtree(file_path)
                    pass
            print(f"已清空文件夹: {folder}")
        else:
            print(f"文件夹不存在: {folder}")

# 用法示例
if __name__ == "__main__":
    clean_folders(["analyze", "wiki", "result"])