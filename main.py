import os
import requests
import feedparser
import json
import base64
import hashlib
from bs4 import BeautifulSoup

# --- (بخش ۱: بارگذاری تنظیمات - بدون تغییر) ---
def load_config():
    sources_json = os.getenv('SOURCES_CONFIG')
    if not sources_json: raise ValueError("خطا: متغیر محیطی SOURCES_CONFIG تعریف نشده است.")
    config = {
        'wp_url': os.getenv('WP_URL'),
        'wp_user': os.getenv('WP_USER'),
        'wp_password': os.getenv('WP_PASSWORD'),
        'sources': json.loads(sources_json)
    }
    for key in ['wp_url', 'wp_user', 'wp_password']:
        if not config[key]: raise ValueError(f"خطا: متغیر محیطی {key.upper()} تعریف نشده است.")
    credentials = f"{config['wp_user']}:{config['wp_password']}"
    token = base64.b64encode(credentials.encode()).decode('utf-8')
    config['wp_headers'] = { 'Authorization': f'Basic {token}', 'Content-Type': 'application/json', 'User-Agent': 'Python-Flexible-Bot/1.0' }
    return config

# --- تابع جدید و انعطاف‌پذیر برای استخراج محتوای تصویری ---
def get_best_visual_content(entry):
    """بهترین محتوای تصویری ممکن (ویدیو یا عکس) را از آیتم فید استخراج می‌کند."""
    
    # اولویت ۱: تلاش برای پیدا کردن ویدیو Embed از طریق اسکرپینگ
    page_url = entry.get('link')
    if page_url:
        print(f"  -> Attempting to scrape for video embed: {page_url}")
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            response = requests.get(page_url, headers=headers, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            meta_tag = soup.find('meta', property='og:video:url')
            if meta_tag and meta_tag.get('content'):
                embed_url = meta_tag['content']
                print(f"  [Success] Found real video embed URL: {embed_url}")
                # ساخت کد iframe واکنش‌گرا
                return f'<div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; height: auto;"><iframe src="{embed_url}" width="100%" height="100%" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;" frameborder="0" scrolling="no" allowfullscreen="true"></iframe></div>'
        except requests.exceptions.RequestException as e:
            print(f"  [Warning] Scraping failed: {e}. Falling back to thumbnail.")
    
    # اولویت ۲: تلاش برای پیدا کردن عکس بندانگشتی در خود فید
    if 'media_thumbnail' in entry and entry.media_thumbnail:
        image_url = entry.media_thumbnail[0].get('url')
        if image_url:
            print(f"  [Info] Found media thumbnail in feed: {image_url}")
            return f'<p><img src="{image_url}" alt="{entry.get("title", "image")}" style="max-width:100%; height:auto;" /></p>'
            
    # اولویت ۳: اگر هیچکدام پیدا نشد
    print("  [Warning] No video embed or thumbnail found.")
    return ""

# --- (بخش ارسال پست به وردپرس - بدون تغییر) ---
def post_to_wordpress_custom_api(config, title, content):
    api_url = f"{config['wp_url']}/wp-json/my-poster/v1/create"
    slug = hashlib.sha1(title.encode('utf-8')).hexdigest()[:12]
    post_data = { "title": f"[Media Test] {title}", "content": content, "slug": f"media-test-{slug}", "category_id": 80 }
    print(f"  -> Posting to WordPress...")
    try:
        response = requests.post(api_url, headers=config['wp_headers'], json=post_data, timeout=90)
        response.raise_for_status()
        print(f"  [Success] Post created: {response.json().get('url', 'N/A')}")
        return True
    except requests.exceptions.RequestException as e:
        if e.response: print(f"  [Debug] Response Body: {e.response.text}"); return False

# --- بخش اصلی برنامه ---
def main():
    try:
        config = load_config()
    except Exception as e:
        print(f"[Fatal Error] {e}"); return

    print("\n--- Starting Flexible Media Extractor Script ---")
    
    source = config['sources'][0]
    rss_url = source['rss_url']
    print(f"\n--- Processing Source: {source['name']} ---")
    
    feed = feedparser.parse(rss_url)
    if feed.bozo or not feed.entries:
        print("  [Warning] Feed is empty or could not be parsed."); return
        
    latest_entry = feed.entries[0]
    item_title = latest_entry.get('title', 'No Title')
        
    print(f"\nProcessing the latest item: {item_title}")
    
    # استخراج بهترین محتوای تصویری ممکن
    visual_content_html = get_best_visual_content(latest_entry)
    
    # استخراج متن توضیحات
    text_content = latest_entry.get('summary', '')
    
    # ترکیب محتوای تصویری و متنی
    final_content = visual_content_html + f"<p>{text_content}</p>"
    
    post_to_wordpress_custom_api(config, item_title, final_content)

    print("\n--- Script finished. ---")

if __name__ == "__main__":
    main()
