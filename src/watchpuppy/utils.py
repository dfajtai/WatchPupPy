import os
import datetime

import hashlib


def current_time_str(format='%Y-%m-%d-%H-%M-%S')->str:
    """Returns the current datetiem"""
    return datetime.datetime.now().strftime(format)


def log_timestamp(format='%Y.%m.%d %H:%M:%S.%f')->str:
    """Returns the current datetiem"""
    return datetime.datetime.now().strftime(format)


def parse_time_str(datetime_str:str,format='%Y-%m-%d-%H-%M-%S')-> datetime.datetime:
    try:
        return datetime.datetime.strptime(datetime_str,format)        
    except ValueError:
        return None
    
    
def md5_for_file(filepath: str, blocksize=65536) -> str:
    """Fast, memory efficient md5 computation"""
    md5 = hashlib.md5()
    try:
        with open(filepath, "rb") as f:
            for block in iter(lambda: f.read(blocksize), b""):
                md5.update(block)
        return md5.hexdigest()
    except Exception as e:
        return "" 