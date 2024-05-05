import os
import shutil
import logging

def copy_files(source_dir: str, target_dir: str):
    """
    Copy files from source_dir to target_dir, logging whether files are new or being overwritten.
    """
    if not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)

    for item in os.listdir(source_dir):
        source_item = os.path.join(source_dir, item)
        target_item = os.path.join(target_dir, item)

        if os.path.isfile(source_item):
            if os.path.exists(target_item):
                logging.info(f"Overwriting existing file: {target_item}")
            else:
                logging.info(f"Creating new file: {target_item}")
            shutil.copy2(source_item, target_item)
        elif os.path.isdir(source_item):
            copy_files(source_item, target_item)

def setup_memgpt_templates():
    """
    Copy templates from 'ella_memgpt/templates' to '~/.memgpt', including humans, presets, personas, and now functions.
    """
    base_source_dir = os.path.join(os.getcwd(), "ella_memgpt", "templates")
    base_target_dir = os.path.join(os.path.expanduser("~"), ".memgpt")

    # Include 'functions' in the list of directories to copy
    for folder_name in ["humans", "presets", "personas", "functions"]:
        source_dir = os.path.join(base_source_dir, folder_name)
        target_dir = os.path.join(base_target_dir, folder_name)

        logging.info(f"Copying {folder_name} from {source_dir} to {target_dir}")
        copy_files(source_dir, target_dir)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    setup_memgpt_templates()
