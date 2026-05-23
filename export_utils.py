import os
from logging import log, INFO
from zipfile import ZipFile, ZIP_DEFLATED

def export_as_zip(texts: list[str], chat_id: int, work_dir: str):
    log(INFO, f'created tempdir for {chat_id} at {work_dir}')

    file_paths = []
    file_id = 1

    for text in texts:
        path = os.path.join(work_dir, f'text{file_id}.txt')

        with open(path, 'w', encoding='utf-8') as file:
            file.write(text)

        file_paths.append(path)
        log(INFO, f'created {path} for {chat_id}')
        file_id += 1

    zip_path = os.path.join(work_dir, 'result.zip')

    with ZipFile(zip_path, 'w', ZIP_DEFLATED) as zipf:
        log(INFO, f'created zip archive {zip_path} for {chat_id}')

        for path in file_paths:
            log(INFO, f'added {path} to archive for {chat_id}')
            zipf.write(path, arcname=os.path.basename(path))
