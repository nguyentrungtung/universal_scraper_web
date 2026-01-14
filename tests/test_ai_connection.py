import asyncio
import litellm
import json
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

async def test_ai_connection(provider, model, api_key, base_url=None, proxy=None):
    print(f"\n{'='*50}")
    print(f"TESTING CONNECTION:")
    print(f"Provider: {provider}")
    print(f"Model:    {model}")
    print(f"Base URL: {base_url}")
    print(f"Proxy:    {proxy}")
    print(f"{'='*50}")

    # Normalize model name like in our provider
    if provider == "google":
        full_model = f"gemini/{model}"
    elif provider == "openai":
        full_model = f"openai/{model}"
    else:
        full_model = f"{provider}/{model}"

    messages = [{"role": "user", "content": "Say 'Connection Successful'"}]
    
    kwargs = {
        "model": full_model,
        "messages": messages,
        "api_key": api_key,
        "base_url": base_url,
        "timeout": 30
    }
    
    if proxy:
        kwargs["proxy"] = proxy

    try:
        print("Sending request...")
        response = await litellm.acompletion(**kwargs)
        print(f"SUCCESS!")
        print(f"Response: {response.choices[0].message.content}")
    except Exception as e:
        print(f"FAILED!")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")
        
        if "NotFoundError" in str(e) and provider == "google":
            print("\nTIP: If you are using a local bridge (like LM Studio or a custom OpenAI-compatible proxy),")
            print("try setting the Provider to 'openai' instead of 'google' in the UI.")

if __name__ == "__main__":
    # User's specific configuration
    USER_API_KEY = "sk-119cba83b57f4e52884ff338ba0e60bf"
    USER_BASE_URL = "http://127.0.0.1:8045/v1"
    USER_MODEL = "gemini-3.0-pro"
    
    # Scenario 1: Using 'google' provider with base_url (Often fails with local bridges)
    print("\n>>> Scenario 1: Provider='google', Base URL='http://127.0.0.1:8045/v1'")
    asyncio.run(test_ai_connection("google", USER_MODEL, USER_API_KEY, base_url=USER_BASE_URL))
    
    # Scenario 2: Using 'openai' provider with base_url (Recommended for local bridges)
    print("\n>>> Scenario 2: Provider='openai', Base URL='http://127.0.0.1:8045/v1'")
    asyncio.run(test_ai_connection("openai", USER_MODEL, USER_API_KEY, base_url=USER_BASE_URL))

    # Scenario 3: Using a network proxy (e.g. Clah/V2Ray) to reach a cloud model
    # This is what happens when you fill the "Proxy Configuration" in the UI
    print("\n>>> Scenario 3: Network Proxy Test (e.g. SOCKS5/HTTP tunnel)")
    # Note: This will only work if you have a proxy running at 8045 that is a SOCKS/HTTP proxy, 
    # NOT an OpenAI bridge.
    asyncio.run(test_ai_connection("google", USER_MODEL, USER_API_KEY, proxy="http://127.0.0.1:8045"))
