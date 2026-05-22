import hashlib


def hash_text_sha256(text):
    """计算精确 UTF-8 文本的 SHA-256。"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def hash_file_sha256(path, chunk_size=1024 * 1024):
    """流式计算文件 SHA-256 和大小。"""
    digest = hashlib.sha256()
    size_bytes = 0
    with path.open("rb") as file_obj:
        while True:
            chunk = file_obj.read(chunk_size)
            if not chunk:
                break
            size_bytes += len(chunk)
            digest.update(chunk)
    return {"sha256": digest.hexdigest(), "size_bytes": size_bytes}


def collect_reviewed_file_hashes(project_path, selected_files):
    """收集被审查文件的相对路径、hash 和大小，不输出文件内容。"""
    reviewed_files = []
    for file_path in selected_files:
        relative_path = str(file_path.relative_to(project_path)).replace("\\", "/")
        entry = {"path": relative_path}
        try:
            entry.update(hash_file_sha256(file_path))
        except OSError as error:
            entry.update({"sha256": None, "size_bytes": None, "read_error": str(error)})
        reviewed_files.append(entry)
    return reviewed_files
