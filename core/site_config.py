import json
import os
from typing import Dict, Any
from config.settings import CRAWL_CONFIG
from urllib.parse import urlparse

class SiteConfigManager:
    CONFIG_FILE = "config/site_configs.json"

    @staticmethod
    def _load_configs() -> Dict[str, Any]:
        if not os.path.exists(SiteConfigManager.CONFIG_FILE):
            return {}
        try:
            with open(SiteConfigManager.CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading site configs: {e}")
            return {}

    @staticmethod
    def get_site_config(url: str) -> Dict[str, Any]:
        """
        Returns optimal configuration for specific domains by matching domain in URL.
        """
        # Default config
        config = {
            "wait_until": "domcontentloaded",
            "wait_for": "body",
            "js_code": [],
            "timeout": CRAWL_CONFIG.get("DEFAULT_TIMEOUT", 60000),
            "scroll_mode": False,
            "scroll_depth": 5
        }

        domain = urlparse(url).netloc.lower()
        # Remove www. if present
        if domain.startswith("www."):
            domain = domain[4:]

        site_configs = SiteConfigManager._load_configs()
        
        # Check for exact match or substring match (e.g. 'batdongsan.com.vn' in 'm.batdongsan.com.vn')
        matched_key = None
        for key in site_configs:
            if key in domain:
                matched_key = key
                break
        
        if matched_key:
            # Merge custom config into default config
            custom_config = site_configs[matched_key]
            config.update(custom_config)
            
        return config
