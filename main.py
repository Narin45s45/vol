import os
import requests
import feedparser
import json
import base64
import hashlib
from urllib.parse import urlparse

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
    config['wp_headers'] = { 'Authorization': f'Basic {token}', 'Content-Type': 'application/json', 'User-Agent': 'Python-Final-Bot/Working' }
    return config

# --- تابع نهایی برای ساخت کد Embed ---
def create_video_embed(page_url):
    """با استفاده از الگوی صحیح، کد iframe را می‌سازد."""
    try:
        # استخراج مسیر از URL اصلی
        path = urlparse(page_url).path
        
        # ساخت URL صحیح برای embed
        embed_url = f"https://www.ign.com/video-embed?url={path}"
        
        print(f"  [Success] Created the correct embed URL: {embed_url}")
        
        # ساخت کد کامل iframe
        video_html = f'<div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; height: auto;"><iframe src="{embed_url}" width="100%" height="100%" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;" frameborder="0" scrolling="no" allowfullscreen="true"></iframe></div>'
        return video_html
    except Exception as e:
        print(f"  [Error] Failed to create embed code: {e}")
        return ""

# --- (بخش ارسال پست به وردپرس - بدون تغییر) ---
def post_to_wordpress_custom_api(config, title, content):
    api_url = f"{config['wp_url']}/wp-json/my-poster/v1/create"
    slug = hashlib.sha1(title.encode('utf-8')).hexdigest()[:12]
    post_data = { "title": f"[Final-Working-Video] {title}", "content": content, "slug": f"final-working-video-{slug}", "category_id": 80 }
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

    print("\n--- Starting The Final Video Posting Script ---")
    
    source = config['sources'][0]
    rss_url = source['rss_url']
    print(f"\n--- Processing Source: {source['name']} ---")
    
    feed = feedparser.parse(rss_url)
    if feed.bozo or not feed.entries:
        print("  [Warning] Feed is empty or could not be parsed."); return
        
    latest_entry = feed.entries[0]
    item_title = latest_entry.get('title', 'No Title')
    item_link = latest_entry.get('link')

    if not item_link:
        print("  [Error] No link found for the latest item."); return
        
    print(f"\nProcessing the latest item: {item_title}")
    
    # استخراج ویدیو با الگوی صحیحی که شما پیدا کردید
    video_html = create_video_embed(item_link)
    
    text_content = latest_entry.get('summary', '')
    final_content = video_html + f"<p>{text_content}</p>"
    
    post_to_wordpress_custom_api(config, item_title, final_content)

    print("\n--- Script finished. ---")

if __name__ == "__main__":
    main()
