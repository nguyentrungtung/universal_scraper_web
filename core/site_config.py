import json
import os
import glob
from typing import Dict, Any
from urllib.parse import urlparse
from loguru import logger

class SiteConfigManager:
    CONFIG_DIR = "config/sites"
    DEFAULT_CONFIG_FILE = "default.json"

    @staticmethod
    def _load_config_file(filename: str) -> Dict[str, Any]:
        path = os.path.join(SiteConfigManager.CONFIG_DIR, filename)
        if not os.path.exists(path):
            return {}
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading config file {filename}: {e}")
            return {}

    @staticmethod
    def get_site_config(url: str) -> Dict[str, Any]:
        """
        Returns optimal configuration for specific domains by matching domain in URL.
        """
        # 1. Load Default Config
        config = SiteConfigManager._load_config_file(SiteConfigManager.DEFAULT_CONFIG_FILE)

        # 2. Determine Domain
        try:
            domain = urlparse(url).netloc.lower()
            # Remove www. if present
            if domain.startswith("www."):
                domain = domain[4:]
        except:
            domain = ""

        if not domain:
            return config

        # 3. Find Matching Config File
        # Strategy: Look for files that match the domain or part of it.
        # e.g. "batdongsan.com.vn.json" matches "batdongsan.com.vn"
        
        # We search for any json file in the directory
        search_pattern = os.path.join(SiteConfigManager.CONFIG_DIR, "*.json")
        candidate_files = glob.glob(search_pattern)
        
        matched_file = None
        # Sort by length descending to match most specific first (e.g. sub.domain.com vs domain.com)
        # But here we just match filename to domain
        
        for file_path in candidate_files:
            filename = os.path.basename(file_path)
            if filename == SiteConfigManager.DEFAULT_CONFIG_FILE:
                continue
                
            # Remove .json extension
            site_key = filename.replace(".json", "")
            
            if site_key in domain:
                matched_file = filename
                break
        
        if matched_file:
            logger.info(f"Loaded site config from {matched_file}")
            custom_config = SiteConfigManager._load_config_file(matched_file)
            config.update(custom_config)
            
        return config
