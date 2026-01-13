import json
import csv
import os
from typing import Any, List, Dict
from datetime import datetime
from loguru import logger
import shutil
from config.settings import PATHS_CONFIG

def save_as_json(data: Any, filename: str):
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        logger.info(f"Saved data to {filename}")
    except Exception as e:
        logger.error(f"Failed to save JSON: {e}")

def save_as_csv(data: List[Dict[str, Any]], filename: str):
    if not data:
        logger.warning("No data to save as CSV")
        return
    
    try:
        keys = data[0].keys()
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            dict_writer = csv.DictWriter(f, fieldnames=keys)
            dict_writer.writeheader()
            dict_writer.writerows(data)
        logger.info(f"Saved data to {filename}")
    except Exception as e:
        logger.error(f"Failed to save CSV: {e}")

def ensure_dir(directory: str):
    if not os.path.exists(directory):
        os.makedirs(directory)

def clean_up_workspace(clean_logs: bool = True, clean_outputs: bool = True) -> str:
    messages = []
    
    if clean_logs:
        log_dir = PATHS_CONFIG["LOG_DIR"]
        if os.path.exists(log_dir):
            try:
                for filename in os.listdir(log_dir):
                    file_path = os.path.join(log_dir, filename)
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                messages.append(f"Cleaned logs in {log_dir}")
            except Exception as e:
                messages.append(f"Failed to clean logs: {e}")
        
        # Also clean main log file
        main_log = PATHS_CONFIG["MAIN_LOG_FILE"]
        if os.path.exists(main_log):
            try:
                os.unlink(main_log)
                messages.append(f"Deleted {main_log}")
            except Exception as e:
                messages.append(f"Failed to delete {main_log}: {e}")

    if clean_outputs:
        output_dir = PATHS_CONFIG["OUTPUT_DIR"]
        if os.path.exists(output_dir):
            try:
                for filename in os.listdir(output_dir):
                    file_path = os.path.join(output_dir, filename)
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                messages.append(f"Cleaned outputs in {output_dir}")
            except Exception as e:
                messages.append(f"Failed to clean outputs: {e}")
                
    return "\n".join(messages)
