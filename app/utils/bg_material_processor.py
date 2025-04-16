import asyncio
import logging
import os
import random
from typing import Optional, TextIO, Callable

import portalocker
from pydantic import FilePath

from app.utils import BackgroundJobManager

"""
Process material files in the background including processing the RAG pipeline for the course
material and the grading pipeline for the assignment. When an API endpoint submits course material,
it gets saved to a file and this background task scans that predefined directory for stuff to process.
The reason we do it like this is because:
1. Grading/RAG pipeline takes too long and API clients might timeout.
2. Holding all the course materials might be bad for memory.
3. If the process is killed, we don't want to lose the request.
4. In production, there might be multiple processes of FastAPI that are truly parallel so this
   approach has the added advantage of true multi-threading (not usually easily possible in Python).
"""


class BackgroundMaterialProcessor:
    save_dir: FilePath
    job_manager: BackgroundJobManager

    def __init__(self, save_dir: FilePath):
        if not save_dir.exists():
            save_dir.mkdir(parents=True)
        if not save_dir.is_dir():
            raise ValueError(f"save_dir must be a directory, got {save_dir}")
        self.save_dir = save_dir
        self.job_manager = BackgroundJobManager(num_threads=4)

    async def start_task_scan_loop(self):
        while True:
            files = os.listdir(self.save_dir)
            # randomly permute to improve the chances
            # of a fair distribution between processes
            random.shuffle(files)
            for file in files:
                self.job_manager.submit_job(
                    self.process,
                    self.save_dir / file,
                    self.process_course_material_job if
                    # TODO: is this even a good way?
                    file.startswith("course_material_job_")
                    else self.process_grading,
                )
                # add a small random delay between to improve the
                # chances of a fair distribution between processes
                await asyncio.sleep(random.random())
            # sleep for 30 seconds
            await asyncio.sleep(30)

    @classmethod
    def process(cls, file_path: FilePath, process_func: Callable[[TextIO], None] = None):
        f = cls.open_file_with_lock(file_path, "r+")
        if f is None:
            return
        content = f.read()
        # if the file is empty, it was already processed
        if not content.strip():
            logging.info(f"{file_path} already processed. Skipping.")
            cls.safe_delete(file_path)
            f.close()
            return
        logging.info(f"Processing {file_path}")
        process_func(f)
        # can't delete the file in all platforms without releasing the lock
        # and so to prevent duplicate processing (since we will need to release the
        # lock to actually delete it), we first wipe the contents of the file
        f.seek(0)
        f.truncate()
        f.close()
        # attempt safe deletion
        cls.safe_delete(file_path)

    @classmethod
    def process_grading(cls, io: TextIO):
        ...

    @classmethod
    def process_course_material_job(cls, io: TextIO):
        ...

    """
    Open a file for reading and locking it. Must do so since there might be multiple processes
    trying to read the same file.
    """

    @classmethod
    def open_file_with_lock(cls, file_path: FilePath, mode: str) -> Optional[TextIO]:
        try:
            lockfile = open(file_path, mode)
            portalocker.lock(lockfile, portalocker.LOCK_EX | portalocker.LOCK_NB)
            return lockfile
        except portalocker.exceptions.LockException:
            return None

    @classmethod
    def safe_delete(cls, path):
        try:
            os.remove(path)
        except FileNotFoundError:
            pass  # Already deleted, no worries
        except PermissionError:
            logging.warning(f"Couldn't delete {path}: Permission denied")
        except Exception as e:
            logging.warning(f"Failed to delete {path}: {e}")
