import os
import requests
import base64
from datetime import datetime
import time

# --- ۱. خواندن متغیرها از GitHub Secrets ---
# این نام‌ها دقیقاً با نام‌هایی که در اسکرین‌شات شما بود، مطابقت دارند
WP_URL = os.environ.get("WP_URL")
WP_USER = os.environ.get("WP_USER")
WP_PASSWORD = os.environ.get("WP_PASSWORD")

# آدرس API سفارشی شما (که از کد موفق شما الگوبرداری شده)
CUSTOM_API_ENDPOINT = f"{WP_URL}/wp-json/my-poster/v1/create"

# بررسی اولیه برای اطمینان از وجود متغیرها
if not all([WP_URL, WP_USER, WP_PASSWORD]):
    raise ValueError("خطا: یکی از متغیرهای WP_URL, WP_USER, یا WP_PASSWORD در GitHub Secrets تعریف نشده است.")

def send_test_post():
    """یک پست تستی برای بررسی اتصال به API سفارشی وردپرس ارسال می‌کند."""
    print(f"Attempting to connect to custom endpoint: {CUSTOM_API_ENDPOINT}")

    # --- ۲. ساخت هدر Authorization (الگوی موفق شما) ---
    credentials = f"{WP_USER}:{WP_PASSWORD}"
    token = base64.b64encode(credentials.encode()).decode('utf-8')
    headers = {
        'Authorization': f'Basic {token}',
        'Content-Type': 'application/json',
        'User-Agent': 'GitHub-Actions-Test-Script/2.0'
    }

    # --- ۳. آماده‌سازی محتوای پست تستی ---
    unique_slug = f"github-final-test-{int(time.time())}"
    post_data = {
        "title": f"پست تست نهایی - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "content": "این پست با موفقیت از طریق API سفارشی ارسال شد. اتصال برقرار است.",
        "slug": unique_slug,
        "category_id": 80 # ID دسته‌بندی که مشخص کردید
    }

    try:
        # --- ۴. ارسال درخواست به وردپرس ---
        print("Sending test post to WordPress...")
        response = requests.post(CUSTOM_API_ENDPOINT, headers=headers, json=post_data, timeout=60)
        
        # بررسی پاسخ از سرور
        response.raise_for_status()
        response_data = response.json()
        
        if response.status_code == 201 and response_data.get("post_id"):
            print("\n✅✅✅ اتصال موفقیت‌آمیز بود! ✅✅✅")
            print("پست تستی با موفقیت در سایت شما ایجاد شد.")
            print(f"آدرس پست: {response_data.get('url', 'N/A')}")
        else:
            print("\n❌ اتصال برقرار شد، اما پست ایجاد نشد.")
            print(f"پاسخ سرور: {response_data}")

    except requests.exceptions.RequestException as e:
        print("\n❌❌❌ خطای اتصال به وردپرس! ❌❌❌")
        print(f"نوع خطا: {type(e).__name__}")
        if e.response is not None:
            print(f"جزئیات پاسخ سرور: Status Code: {e.response.status_code}")
            print(f"Response Body: {e.response.text}")
        else:
            print(f"پیام خطا: {e}")

if __name__ == "__main__":
    send_test_post()
