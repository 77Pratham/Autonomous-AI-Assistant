import os

def create_folder(folder_name: str, path: str = "/usr/src/app/data/output") -> dict:
    """
    Creates a new folder at a specified path inside the container.

    Args:
        folder_name: The name of the folder to create.
        path: The base path where the folder will be created.

    Returns:
        A dictionary with the status of the operation.
    """
    if not folder_name or not isinstance(folder_name, str):
        return {"status": "error", "message": "Invalid folder name provided."}

    # Sanitize folder name to prevent directory traversal attacks
    folder_name = os.path.basename(folder_name)
    full_path = os.path.join(path, folder_name)

    try:
        os.makedirs(full_path, exist_ok=True)
        message = f"Folder '{folder_name}' created successfully at {full_path}."
        print(message)
        return {"status": "success", "message": message}
    except Exception as e:
        message = f"Failed to create folder '{folder_name}'. Error: {e}"
        print(message)
        return {"status": "error", "message": str(e)}
