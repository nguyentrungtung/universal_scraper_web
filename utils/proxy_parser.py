import re
from typing import Optional, List
from models.scraper_input import ProxyConfig

def parse_proxy_string(proxy_str: str) -> Optional[ProxyConfig]:
    """
    Parses a single proxy string in various formats.
    """
    if not proxy_str or not proxy_str.strip():
        return None

    proxy_str = proxy_str.strip()
    
    # Pattern for [protocol://][user:pass@]ip:port
    pattern = r'^(?:(?P<protocol>\w+)://)?(?:(?P<user>[^:@]+):(?P<pass>[^:@]+)@)?(?P<host>[^:@]+):(?P<port>\d+)$'
    match = re.match(pattern, proxy_str)
    
    if match:
        groups = match.groupdict()
        protocol = groups.get('protocol') or 'http'
        host = groups.get('host')
        port = groups.get('port')
        user = groups.get('user')
        password = groups.get('pass')
        
        server = f"{protocol}://{host}:{port}"
        return ProxyConfig(server=server, username=user, password=password)
    
    # Fallback for simple ip:port
    if ':' in proxy_str and '@' not in proxy_str:
        return ProxyConfig(server=f"http://{proxy_str}")
        
    return None

def parse_proxy_list(proxy_text: str) -> List[ProxyConfig]:
    """
    Parses a multi-line string containing multiple proxies.
    """
    if not proxy_text:
        return []
    
    proxies = []
    lines = proxy_text.strip().split('\n')
    for line in lines:
        p = parse_proxy_string(line.strip())
        if p:
            proxies.append(p)
    return proxies
