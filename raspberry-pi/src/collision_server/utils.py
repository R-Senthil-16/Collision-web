"""
Utility functions for the Collision Detection Server
"""
import os
from typing import List


# Supported video file extensions
ALLOWED_EXTENSIONS = {'.mp4', '.avi', '.mov', '.webm'}


def allowed_file(filename: str) -> bool:
    """Check if file has an allowed extension"""
    if not filename:
        return False
    
    file_extension = get_file_extension(filename)
    return file_extension.lower() in ALLOWED_EXTENSIONS


def get_file_extension(filename: str) -> str:
    """Get file extension from filename"""
    return os.path.splitext(filename)[1]


def get_supported_formats() -> List[str]:
    """Get list of supported video formats"""
    return list(ALLOWED_EXTENSIONS)


def validate_video_format(file_path: str) -> bool:
    """Validate that a file is a supported video format"""
    if not os.path.exists(file_path):
        return False
    
    return allowed_file(file_path)


def ensure_directory_exists(directory_path: str) -> None:
    """Ensure a directory exists, create if it doesn't"""
    os.makedirs(directory_path, exist_ok=True)


def get_file_size(file_path: str) -> int:
    """Get file size in bytes"""
    if not os.path.exists(file_path):
        return 0
    return os.path.getsize(file_path)


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"