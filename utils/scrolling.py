from typing import List

def get_infinite_scroll_js(max_scrolls: int = 5, delay_ms: int = 2000) -> List[str]:
    """
    Generates a list of JS commands for sequential execution.
    This is more reliable for crawlers to await each step.
    """
    commands = []
    for i in range(max_scrolls):
        # Scroll to bottom
        commands.append("window.scrollTo(0, document.body.scrollHeight);")
        # Wait for content to load
        commands.append(f"new Promise(r => setTimeout(r, {delay_ms}));")
    return commands

def get_scroll_to_element_js(selector: str) -> str:
    """
    Generates JS to scroll a specific element into view.
    """
    return f"""
    (function() {{
        const el = document.querySelector('{selector}');
        if (el) {{
            el.scrollIntoView({{behavior: 'smooth', block: 'center'}});
            return true;
        }}
        return false;
    }})();
    """
