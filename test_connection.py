import os
import requests
import base64
from datetime import datetime

WP_URL = os.environ.get("WORDPRESS_URL")
WP_USER = os.environ.get("WORDPRESS_USER")
WP_PASS = os.environ.get("WORDPRESS_PASS")
CUSTOM_API_ENDPOINT = f"{WP_URL}/wp-json/wp/v2/posts" # استفاده از API استاندارد وردپرس

if not all([WP_URL, WP_USER, WP_PASS]):
    raise ValueError("یکی از متغیرهای WORDPRESS_URL, WORDPRESS_USER, یا WORDPRESS_PASS تعریف نشده است.")

def create_test_post():
    print(f"Attempting to post to: {CUSTOM_API_ENDPOINT}")
    credentials = f"{WP_USER}:{WP_PASS}"
    token = base64.b64encode(credentials.encode()).decode('utf-8')
    headers = {
        'Authorization': f'Basic {token}',
        'Content-Type': 'application/json'
    }
    post_data = {
        "title": f"Test Post from GitHub - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "content": "This is a test post to verify the connection.",
        "status": "draft" # ارسال به صورت پیش‌نویس
    }
    try:
        response = requests.post(CUSTOM_API_ENDPOINT, headers=headers, json=post_data, timeout=60)
        response.raise_for_status()
        print("\n✅ Connection Successful! Post created as a draft.")
        print(f"Response: {response.json()}")
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Connection Error!")
        print(f"Error Type: {type(e).__name__}")
        if e.response is not None:
            print(f"Server Response: {e.response.status_code} - {e.response.text}")
        else:
            print(f"Error Message: {e}")

if __name__ == "__main__":
    create_test_post()
