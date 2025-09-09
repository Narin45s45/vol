import os
import requests
import base64
import json

# --- ۱. خواندن تنظیمات اصلی ---
WP_URL = os.environ.get("WP_URL")
WP_USER = os.environ.get("WP_USER")
WP_PASSWORD = os.environ.get("WP_PASSWORD")

if not all([WP_URL, WP_USER, WP_PASSWORD]):
    raise ValueError("یکی از متغیرهای WP_URL, WP_USER, یا WP_PASSWORD تعریف نشده است.")

# --- ۲. تعریف کد iframe و آدرس API ---
# این همان کد iframe موفقی است که شما پیدا کردید
IFRAME_CODE = '<iframe src="https://www.ign.com/video-embed?url=/videos/why-silksong-fans-are-debating-the-games-difficulty" frameborder="0" width="850" height="800"></iframe>'
API_ENDPOINT = f"{WP_URL}/wp-json/my-poster/v1/create"

def send_iframe_test():
    """فقط یک پست حاوی کد iframe ارسال می‌کند."""
    print(f"Attempting to post a simple iframe to: {API_ENDPOINT}")

    # ساخت هدر Authorization
    credentials = f"{WP_USER}:{WP_PASSWORD}"
    token = base64.b64encode(credentials.encode()).decode('utf-8')
    headers = {
        'Authorization': f'Basic {token}',
        'Content-Type': 'application/json'
    }

    # آماده‌سازی محتوای پست
    post_data = {
        "title": "[IFRAME TEST] - تست نهایی آی‌فریم",
        "content": IFRAME_CODE,
        "slug": "iframe-final-test",
        "category_id": 80
    }
    
    print("Sending the following data to WordPress:")
    print(json.dumps(post_data, indent=2))

    try:
        # ارسال درخواست
        response = requests.post(API_ENDPOINT, headers=headers, json=post_data, timeout=60)
        response.raise_for_status()
        print("\n✅ Success! The post was sent to WordPress without a connection error.")
        print(f"New Post URL: {response.json().get('url', 'N/A')}")
        print("\nPlease check the post on your website to see if the iframe was saved or stripped.")

    except requests.exceptions.RequestException as e:
        print(f"\n❌ Error! Could not post to WordPress.")
        if e.response is not None:
            print(f"Server Response: {e.response.status_code} - {e.response.text}")
        else:
            print(f"Error Message: {e}")

if __name__ == "__main__":
    send_iframe_test()
