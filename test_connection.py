import os
import requests
import base64
import json
from datetime import datetime

# --- خواندن متغیرهای محیطی ---
# اینها را باید در GitHub Secrets خود تعریف کنید
WP_URL = os.environ.get("WORDPRESS_URL")
WP_USER = os.environ.get("WORDPRESS_USER")
WP_PASS = os.environ.get("WORDPRESS_PASS")

# --- آدرس API سفارشی شما ---
# اگر آدرس API سفارشی در سایت جدید شما متفاوت است، آن را در اینجا تغییر دهید
CUSTOM_API_ENDPOINT = f"{WP_URL}/wp-json/my-poster/v1/create"

# بررسی اینکه آیا متغیرهای اصلی تعریف شده‌اند
if not all([WP_URL, WP_USER, WP_PASS]):
    raise ValueError("متغیرهای محیطی WORDPRESS_URL, WORDPRESS_USER, یا WORDPRESS_PASS تعریف نشده‌اند.")

def create_test_post():
    """یک پست تستی ساده برای بررسی اتصال به وردپرس ارسال می‌کند."""
    print(f"Attempting to post to: {CUSTOM_API_ENDPOINT}")

    # --- الگوی اتصال شما: ساخت توکن Authentication ---
    # این کد دقیقاً از الگوی موفق اسکریپت قبلی شما پیروی می‌کند
    credentials = f"{WP_USER}:{WP_PASS}"
    token = base64.b64encode(credentials.encode())
    headers = {
        'Authorization': f'Basic {token.decode("utf-8")}',
        'Content-Type': 'application/json',
        'User-Agent': 'Python-Test-Connection-Script/1.0'
    }

    # --- محتوای پست تستی ---
    # ما فقط فیلدهای ضروری را برای تست ارسال می‌کنیم
    post_data = {
        "title": f"پست تستی از گیت‌هاب - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "content": "این یک پست تستی است که به صورت خودکار برای بررسی صحت اتصال به API سفارشی وردپرس ارسال شده است.",
        "slug": f"github-test-post-{datetime.now().timestamp()}",
        "category_id": 80 # استفاده از همان ID دسته‌ای که قبلاً مشخص کردید
    }

    try:
        # ارسال درخواست به وردپرس
        response = requests.post(CUSTOM_API_ENDPOINT, headers=headers, json=post_data, timeout=60)
        
        # بررسی پاسخ از سرور
        response.raise_for_status() # اگر کد وضعیت خطا بود (مثلا 404 یا 500)، یک exception ایجاد می‌کند
        
        response_data = response.json()
        
        if response.status_code == 201 and response_data.get("post_id"):
            print("\n✅ اتصال موفقیت‌آمیز بود!")
            print(f"پست تستی با موفقیت ایجاد شد.")
            print(f"آدرس پست: {response_data.get('url', 'N/A')}")
        else:
            print("\n❌ اتصال برقرار شد، اما پست ایجاد نشد.")
            print(f"پاسخ سرور: {response_data}")

    except requests.exceptions.RequestException as e:
        print(f"\n❌ خطای اتصال به وردپرس!")
        print(f"نوع خطا: {type(e).__name__}")
        print(f"پیام خطا: {e}")
        if e.response is not None:
            print(f"جزئیات پاسخ سرور: {e.response.status_code} - {e.response.text}")

if __name__ == "__main__":
    create_test_post()
