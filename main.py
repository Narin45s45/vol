import os
import requests
import feedparser
import json
import base64
import hashlib
import time

# --- بخش ۱: بارگذاری تنظیمات ---
def load_config():
    """تنظیمات را از متغیرهای محیطی گیت‌هاب می‌خواند."""
    sources_json = os.getenv('SOURCES_CONFIG')
    if not sources_json:
        raise ValueError("خطا: متغیر محیطی SOURCES_CONFIG تعریف نشده است.")

    config = {
        'wp_url': os.getenv('WP_URL'),
        'wp_user': os.getenv('WP_USER'),
        'wp_password': os.getenv('WP_PASSWORD'),
        'sources': json.loads(sources_json)
    }
    for key in ['wp_url', 'wp_user', 'wp_password']:
        if not config[key]:
            raise ValueError(f"خطا: متغیر محیطی {key.upper()} تعریف نشده است.")

    credentials = f"{config['wp_user']}:{config['wp_password']}"
    token = base64.b64encode(credentials.encode()).decode('utf-8')
    config['wp_headers'] = {
        'Authorization': f'Basic {token}',
        'Content-Type': 'application/json',
        'User-Agent': 'Python-Raw-Feed-Bot/1.0'
    }
    
    print("[Info] Configuration loaded successfully.")
    return config

# --- بخش ۲: مدیریت آیتم‌های تکراری ---
def get_processed_items_from_wp(config):
    """لیست لینک‌های پردازش شده را از API سفارشی وردپرس دریافت می‌کند."""
    api_url = f"{config['wp_url']}/wp-json/my-poster/v1/processed-links"
    print(f"[Info] Getting processed links from WordPress...")
    try:
        response = requests.get(api_url, headers=config['wp_headers'], timeout=60)
        response.raise_for_status()
        return set(response.json())
    except requests.exceptions.RequestException as e:
        print(f"[Fatal] Could not get processed links: {e}")
        raise

def save_processed_item_to_wp(config, item_link):
    """لینک پردازش شده را در وردپرس ذخیره می‌کند."""
    api_url = f"{config['wp_url']}/wp-json/my-poster/v1/processed-links"
    payload = {"link": item_link}
    print(f"  -> [Info] Saving processed link: {item_link}")
    try:
        response = requests.post(api_url, headers=config['wp_headers'], json=payload, timeout=60)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"  [Error] Failed to save processed link: {e}")
        return False

# --- بخش ۳: ارسال پست به وردپرس ---
def post_to_wordpress_custom_api(config, title, content):
    api_url = f"{config['wp_url']}/wp-json/my-poster/v1/create"
    
    slug = hashlib.sha1(title.encode('utf-8')).hexdigest()[:12]

    post_data = {
        "title": title,
        "content": content,
        "slug": f"raw-{slug}",
        "category_id": 80 # ID دسته‌بندی
    }
    
    print(f"  -> [Info] Posting to WordPress: {title}")
    try:
        response = requests.post(api_url, headers=config['wp_headers'], json=post_data, timeout=90)
        response.raise_for_status()
        print(f"  [Success] Post created successfully.")
        return True
    except requests.exceptions.RequestException as e:
        print(f"  [Error] Failed to post to WordPress: {e}")
        if e.response: print(f"  [Debug] Response Body: {e.response.text}")
        return False

# --- بخش ۴: منطق اصلی برنامه ---
def main():
    try:
        config = load_config()
    except Exception as e:
        print(f"[Fatal Error] {e}")
        return

    print("\n--- Starting Raw Feed Poster Script ---")
    
    processed_items = get_processed_items_from_wp(config)
    
    for source in config['sources']:
        source_name = source['name']
        rss_url = source['rss_url']
        print(f"\n--- Processing Source: {source_name} ---")
        
        feed = feedparser.parse(rss_url)
        if feed.bozo:
            print(f"  [Warning] Error reading RSS feed: {feed.bozo_exception}")
            continue
            
        for entry in reversed(feed.entries):
            item_link = entry.get('link')
            item_title = entry.get('title', 'No Title')
            
            if not item_link or item_link in processed_items:
                continue
                
            print(f"\nProcessing new item: {item_title}")
            
            # استخراج محتوای خام از فید
            raw_content = ""
            if 'content' in entry and entry.content:
                raw_content = entry.content[0].value
            elif 'summary' in entry:
                raw_content = entry.summary
            
            if not raw_content:
                print("  [Warning] No content found. Skipping.")
                save_processed_item_to_wp(config, item_link)
                continue
                
            # ارسال مستقیم محتوای خام به وردپرس
            if post_to_wordpress_custom_api(config, item_title, raw_content):
                save_processed_item_to_wp(config, item_link)

            time.sleep(5)

    print("\n--- Script finished. ---")

if __name__ == "__main__":
    main()
