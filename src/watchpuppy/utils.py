import os
import sys

from typing import Optional

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




def _is_file_locked_posix(filepath: str) -> bool:
    """
    Check if a file is locked by another process on POSIX systems using fcntl.

    Attempts to acquire an exclusive non-blocking lock on the file.
    If the lock is obtained, file is considered unlocked; otherwise locked.

    Args:
        filepath (str): Path to the file to check.

    Returns:
        bool: True if the file is locked by another process, False otherwise.
    """
    import fcntl
    try:
        with open(filepath, 'rb') as f:
            try:
                # Try to acquire an exclusive non-blocking lock
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                # Release the lock immediately
                fcntl.flock(f, fcntl.LOCK_UN)
                return False
            except IOError:
                # Lock could not be acquired, file is locked elsewhere
                return True
    except Exception:
        # If file cannot be opened or other error, treat as not locked
        return False


def _is_file_locked_windows(filepath: str) -> bool:
    """
    Check if a file is locked by another process on Windows systems using msvcrt.

    Attempts to acquire an exclusive non-blocking lock on part of the file.
    If the lock is obtained, file is considered unlocked; otherwise locked.

    Args:
        filepath (str): Path to the file to check.

    Returns:
        bool: True if the file is locked by another process, False otherwise.
    """
    import msvcrt
    try:
        fh = open(filepath, 'rb')
        try:
            # Try to lock 1 byte non-blocking
            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
            # Unlock immediately
            msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
            return False
        except IOError:
            # Lock failed, file is locked elsewhere
            return True
        finally:
            fh.close()
    except Exception:
        # If file cannot be opened or other error, treat as not locked
        return False


def is_file_locked(filepath: str) -> bool:
    """
    Cross-platform interface to check if a file is currently locked by another process.

    Uses platform-appropriate locking method:
    - On Windows, uses msvcrt locking.
    - On POSIX (Linux/macOS), uses fcntl locking.

    Args:
        filepath (str): Path to the file to check.

    Returns:
        bool: True if the file is locked by another process; False if unlocked or unable to determine.
    """
    if not os.path.exists(filepath):
        # File does not exist, treat as not locked
        return False
    
    if sys.platform.startswith('win'):
        return _is_file_locked_windows(filepath)
    else:
        # POSIX-like system (Linux/macOS, etc.)
        return _is_file_locked_posix(filepath)
