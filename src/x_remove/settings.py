import os
from pathlib import Path

def get_app_data_folder(app_name: str) -> Path:
    """Get the path to the application data folder for the given application name.

    Args:
        app_name (str): The name of the application.

    """
    if os.getenv("X_DATA_DIR"):
        base_dir = Path(os.getenv("X_DATA_DIR"))
    else:
        if os.name == 'nt':
            # Windows
            base_dir = Path(os.getenv('APPDATA'))
        else:
            # macOS and Linux
            base_dir = Path(os.getenv('HOME')) / '.local' / 'share'

    app_data_folder = base_dir / app_name
    
    # Create the directory if it doesn't exist
    app_data_folder.mkdir(parents=True, exist_ok=True)
    
    return app_data_folder

APP_NAME = "x-remove.cc"
app_data_folder = get_app_data_folder(APP_NAME)
app_data_folder.mkdir(parents=True, exist_ok=True)
