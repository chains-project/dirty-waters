"""
This file contains the configuration for the tool.
"""

import datetime
import pathlib
import logging

import requests_cache

# change this to the install command for your project
PNPM_LIST_COMMAND = [
    "pnpm",
    "list",
    "--filter",
    "ledger-live-desktop",
    "--depth",
    "Infinity",
]


class PathManager:
    """
    Manage the paths for the results.
    """

    def __init__(self, base_dir="results"):
        self.base_dir = pathlib.Path(base_dir)

    def create_folders(self, version_tag):
        """
        Create the folders for the results.
        """

        current_time = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        folder_name = f"results_{current_time}"
        result_folder_path = self.base_dir / folder_name
        result_folder_path.mkdir(parents=True, exist_ok=True)

        json_directory = result_folder_path / "sscs" / version_tag
        json_directory.mkdir(parents=True, exist_ok=True)
        diff_directory = result_folder_path / "diff"
        diff_directory.mkdir(parents=True, exist_ok=True)

        return result_folder_path, json_directory, diff_directory


def setup_cache(cache_name):
    """
    Setup the cache for the requests.
    """

    cache_folder = pathlib.Path("cache")
    cache_folder.mkdir(parents=True, exist_ok=True)

    cache_file = cache_folder / f"{cache_name}_cache"

    requests_cache.install_cache(
        cache_name=str(cache_file),
        backend="sqlite",
        expire_after=7776000,
        allowable_codes=(200, 301, 302, 404),
    )  # 90 days

    # logging.info(f"Cache setup complete: {cache_file}")


def setup_logger(log_file_path):
    """
    Setup the logger for the analysis.
    """

    # Set up the logger
    logger = logging.getLogger("dw_analysis")
    logger.setLevel(logging.INFO)

    # Create a console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Create a file handler
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(logging.INFO)

    # Create a formatter and set it for both handlers
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # Add the handlers to the logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger
