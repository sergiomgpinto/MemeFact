import logging
import os
from datetime import datetime
from pathlib import Path
from utils.helpers import get_git_root


def setup_logging():
    rep_root_dir = get_git_root()
    log_dir = Path(rep_root_dir) / 'data' / 'bot' / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
    log_file = log_dir / f'xbot_{timestamp}.log'

    logging.basicConfig(
        filename=str(log_file),
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        force=True
    )
    logging.info(f"Log file created at: {log_file}")


def get_logger(name):
    return logging.getLogger(name)


def log_print(*args, **kwargs):
    message = ' '.join(map(str, args))
    logging.info(message)
    print(message, **kwargs)