import os
import shutil
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
import mimetypes
from datetime import datetime

logger = logging.getLogger(__name__)

def create_folder(folder_name: str, path: str = "/usr/src/app/data/output") -> Dict[str, Any]:
    """
    Creates a new folder at a specified path inside the container.

    Args:
        folder_name: The name of the folder to create.
        path: The base path where the folder will be created.

    Returns:
        A dictionary with the status of the operation.
    """
    try:
        if not folder_name or not isinstance(folder_name, str):
            return {"status": "error", "message": "Invalid folder name provided."}

        # Sanitize folder name to prevent directory traversal attacks
        folder_name = os.path.basename(folder_name.strip())
        if not folder_name:
            return {"status": "error", "message": "Folder name cannot be empty after sanitization."}
        
        # Ensure base path exists
        os.makedirs(path, exist_ok=True)
        
        full_path = os.path.join(path, folder_name)
        
        # Check if folder already exists
        if os.path.exists(full_path):
            return {
                "status": "info", 
                "message": f"Folder '{folder_name}' already exists at {full_path}.",
                "path": full_path
            }
        
        # Create the folder
        os.makedirs(full_path, exist_ok=True)
        
        message = f"Folder '{folder_name}' created successfully at {full_path}."
        logger.info(message)
        
        return {
            "status": "success", 
            "message": message,
            "path": full_path,
            "folder_name": folder_name
        }
        
    except Exception as e:
        error_msg = f"Failed to create folder '{folder_name}'. Error: {e}"
        logger.error(error_msg)
        return {"status": "error", "message": str(e)}


def list_files(path: str = "/usr/src/app/data/output", include_hidden: bool = False) -> Dict[str, Any]:
    """
    Lists all files and folders in a directory.
    
    Args:
        path: The directory path to list
        include_hidden: Whether to include hidden files
        
    Returns:
        Dictionary with file and folder information
    """
    try:
        if not os.path.exists(path):
            return {"status": "error", "message": f"Path '{path}' does not exist."}
        
        if not os.path.isdir(path):
            return {"status": "error", "message": f"Path '{path}' is not a directory."}
        
        files = []
        folders = []
        
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            
            # Skip hidden files unless requested
            if not include_hidden and item.startswith('.'):
                continue
            
            # Get item stats
            stats = os.stat(item_path)
            size = stats.st_size
            modified = datetime.fromtimestamp(stats.st_mtime).isoformat()
            
            if os.path.isdir(item_path):
                folders.append({
                    "name": item,
                    "path": item_path,
                    "type": "folder",
                    "modified": modified,
                    "size": get_folder_size(item_path)
                })
            else:
                mime_type, _ = mimetypes.guess_type(item)
                files.append({
                    "name": item,
                    "path": item_path,
                    "type": "file",
                    "size": size,
                    "modified": modified,
                    "mime_type": mime_type,
                    "extension": Path(item).suffix.lower()
                })
        
        return {
            "status": "success",
            "path": path,
            "files": files,
            "folders": folders,
            "total_items": len(files) + len(folders),
            "message": f"Found {len(files)} files and {len(folders)} folders in '{path}'"
        }
        
    except Exception as e:
        error_msg = f"Failed to list files in '{path}'. Error: {e}"
        logger.error(error_msg)
        return {"status": "error", "message": str(e)}


def get_folder_size(folder_path: str) -> int:
    """
    Calculate the total size of a folder.
    
    Args:
        folder_path: Path to the folder
        
    Returns:
        Total size in bytes
    """
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(folder_path):
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                try:
                    total_size += os.path.getsize(file_path)
                except (OSError, FileNotFoundError):
                    continue
    except Exception:
        pass
    return total_size


def delete_file_or_folder(path: str, force: bool = False) -> Dict[str, Any]:
    """
    Delete a file or folder.
    
    Args:
        path: Path to the file or folder to delete
        force: Whether to force delete without confirmation
        
    Returns:
        Dictionary with operation status
    """
    try:
        if not os.path.exists(path):
            return {"status": "error", "message": f"Path '{path}' does not exist."}
        
        # Security check - only allow deletion within specific directories
        allowed_dirs = ["/usr/src/app/data/output", "/tmp"]
        if not any(path.startswith(allowed_dir) for allowed_dir in allowed_dirs):
            return {"status": "error", "message": "Deletion not allowed outside of safe directories."}
        
        item_name = os.path.basename(path)
        
        if os.path.isfile(path):
            os.remove(path)
            message = f"File '{item_name}' deleted successfully."
        elif os.path.isdir(path):
            if force:
                shutil.rmtree(path)
                message = f"Folder '{item_name}' and all its contents deleted successfully."
            else:
                # Check if folder is empty
                if os.listdir(path):
                    return {
                        "status": "error", 
                        "message": f"Folder '{item_name}' is not empty. Use force=True to delete non-empty folders."
                    }
                os.rmdir(path)
                message = f"Empty folder '{item_name}' deleted successfully."
        else:
            return {"status": "error", "message": f"'{path}' is neither a file nor a folder."}
        
        logger.info(message)
        return {"status": "success", "message": message, "deleted_path": path}
        
    except Exception as e:
        error_msg = f"Failed to delete '{path}'. Error: {e}"
        logger.error(error_msg)
        return {"status": "error", "message": str(e)}


def move_file_or_folder(source_path: str, destination_path: str) -> Dict[str, Any]:
    """
    Move a file or folder from source to destination.
    
    Args:
        source_path: Path to the source file/folder
        destination_path: Destination path
        
    Returns:
        Dictionary with operation status
    """
    try:
        if not os.path.exists(source_path):
            return {"status": "error", "message": f"Source path '{source_path}' does not exist."}
        
        # Create destination directory if it doesn't exist
        dest_dir = os.path.dirname(destination_path)
        os.makedirs(dest_dir, exist_ok=True)
        
        # Check if destination already exists
        if os.path.exists(destination_path):
            return {"status": "error", "message": f"Destination '{destination_path}' already exists."}
        
        shutil.move(source_path, destination_path)
        
        source_name = os.path.basename(source_path)
        message = f"'{source_name}' moved successfully from '{source_path}' to '{destination_path}'"
        logger.info(message)
        
        return {
            "status": "success",
            "message": message,
            "source_path": source_path,
            "destination_path": destination_path
        }
        
    except Exception as e:
        error_msg = f"Failed to move '{source_path}' to '{destination_path}'. Error: {e}"
        logger.error(error_msg)
        return {"status": "error", "message": str(e)}


def copy_file_or_folder(source_path: str, destination_path: str) -> Dict[str, Any]:
    """
    Copy a file or folder from source to destination.
    
    Args:
        source_path: Path to the source file/folder
        destination_path: Destination path
        
    Returns:
        Dictionary with operation status
    """
    try:
        if not os.path.exists(source_path):
            return {"status": "error", "message": f"Source path '{source_path}' does not exist."}
        
        # Create destination directory if it doesn't exist
        dest_dir = os.path.dirname(destination_path)
        os.makedirs(dest_dir, exist_ok=True)
        
        # Check if destination already exists
        if os.path.exists(destination_path):
            return {"status": "error", "message": f"Destination '{destination_path}' already exists."}
        
        if os.path.isfile(source_path):
            shutil.copy2(source_path, destination_path)
        else:
            shutil.copytree(source_path, destination_path)
        
        source_name = os.path.basename(source_path)
        message = f"'{source_name}' copied successfully from '{source_path}' to '{destination_path}'"
        logger.info(message)
        
        return {
            "status": "success",
            "message": message,
            "source_path": source_path,
            "destination_path": destination_path
        }
        
    except Exception as e:
        error_msg = f"Failed to copy '{source_path}' to '{destination_path}'. Error: {e}"
        logger.error(error_msg)
        return {"status": "error", "message": str(e)}


def create_file(file_name: str, content: str = "", path: str = "/usr/src/app/data/output") -> Dict[str, Any]:
    """
    Create a new file with optional content.
    
    Args:
        file_name: Name of the file to create
        content: Content to write to the file
        path: Directory where the file should be created
        
    Returns:
        Dictionary with operation status
    """
    try:
        if not file_name or not isinstance(file_name, str):
            return {"status": "error", "message": "Invalid file name provided."}
        
        # Sanitize file name
        file_name = os.path.basename(file_name.strip())
        if not file_name:
            return {"status": "error", "message": "File name cannot be empty after sanitization."}
        
        # Ensure directory exists
        os.makedirs(path, exist_ok=True)
        
        full_path = os.path.join(path, file_name)
        
        # Check if file already exists
        if os.path.exists(full_path):
            return {
                "status": "info",
                "message": f"File '{file_name}' already exists at {full_path}",
                "path": full_path
            }
        
        # Create the file
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        message = f"File '{file_name}' created successfully at {full_path}"
        logger.info(message)
        
        return {
            "status": "success",
            "message": message,
            "path": full_path,
            "file_name": file_name,
            "size": len(content.encode('utf-8'))
        }
        
    except Exception as e:
        error_msg = f"Failed to create file '{file_name}'. Error: {e}"
        logger.error(error_msg)
        return {"status": "error", "message": str(e)}


def read_file(file_path: str) -> Dict[str, Any]:
    """
    Read the contents of a file.
    
    Args:
        file_path: Path to the file to read
        
    Returns:
        Dictionary with file contents and metadata
    """
    try:
        if not os.path.exists(file_path):
            return {"status": "error", "message": f"File '{file_path}' does not exist."}
        
        if not os.path.isfile(file_path):
            return {"status": "error", "message": f"'{file_path}' is not a file."}
        
        # Check file size (limit to 10MB for safety)
        file_size = os.path.getsize(file_path)
        if file_size > 10 * 1024 * 1024:  # 10MB
            return {"status": "error", "message": f"File is too large ({file_size} bytes). Maximum size is 10MB."}
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {
            "status": "success",
            "path": file_path,
            "content": content,
            "size": file_size,
            "lines": len(content.split('\n')),
            "message": f"File '{os.path.basename(file_path)}' read successfully"
        }
        
    except UnicodeDecodeError:
        return {"status": "error", "message": "File contains non-text content or unsupported encoding."}
    except Exception as e:
        error_msg = f"Failed to read file '{file_path}'. Error: {e}"
        logger.error(error_msg)
        return {"status": "error", "message": str(e)}


def get_file_info(file_path: str) -> Dict[str, Any]:
    """
    Get detailed information about a file or folder.
    
    Args:
        file_path: Path to the file/folder
        
    Returns:
        Dictionary with detailed information
    """
    try:
        if not os.path.exists(file_path):
            return {"status": "error", "message": f"Path '{file_path}' does not exist."}
        
        stats = os.stat(file_path)
        path_obj = Path(file_path)
        
        info = {
            "status": "success",
            "path": file_path,
            "name": path_obj.name,
            "size": stats.st_size,
            "created": datetime.fromtimestamp(stats.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stats.st_mtime).isoformat(),
            "accessed": datetime.fromtimestamp(stats.st_atime).isoformat(),
            "is_file": path_obj.is_file(),
            "is_directory": path_obj.is_dir(),
            "permissions": oct(stats.st_mode)[-3:],
        }
        
        if path_obj.is_file():
            info["extension"] = path_obj.suffix.lower()
            info["mime_type"], _ = mimetypes.guess_type(file_path)
            
        return info
        
    except Exception as e:
        error_msg = f"Failed to get info for '{file_path}'. Error: {e}"
        logger.error(error_msg)
        return {"status": "error", "message": str(e)}