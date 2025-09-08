import os
import requests
import feedparser
import json
import base64
import hashlib

# --- بخش ۱: بارگذاری تنظیمات ---
def load_config():
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
        'User-Agent': 'Python-Raw-Feed-Bot/2.0'
    }
    return config

# --- بخش ۲: ارسال پست به وردپرس ---
def post_to_wordpress_custom_api(config, title, content):
    api_url = f"{config['wp_url']}/wp-json/my-poster/v1/create"
    slug = hashlib.sha1(title.encode('utf-8')).hexdigest()[:12]
    
    post_data = {
        "title": f"[RAW FEED TEST] {title}",
        "content": content, # ارسال مستقیم محتوای خام فید
        "slug": f"raw-feed-test-{slug}",
        "category_id": 80
    }
    print(f"  -> [Info] Posting raw content to WordPress: {title}")
    try:
        response = requests.post(api_url, headers=config['wp_headers'], json=post_data, timeout=90)
        response.raise_for_status()
        print(f"  [Success] Raw test post created successfully.")
        return True
    except requests.exceptions.RequestException as e:
        print(f"  [Error] Failed to post to WordPress: {e}")
        if e.response: print(f"  [Debug] Response Body: {e.response.text}")
        return False

# --- بخش ۳: منطق اصلی برنامه ---
def main():
    try:
        config = load_config()
    except Exception as e:
        print(f"[Fatal Error] {e}")
        return

    print("\n--- Starting Pure Raw Feed Poster (No Parsing) ---")
    
    source = config['sources'][0]
    rss_url = source['rss_url']
    print(f"\n--- Processing Source: {source['name']} ---")
    
    feed = feedparser.parse(rss_url)
    if feed.bozo or not feed.entries:
        print("  [Warning] Feed is empty or could not be parsed.")
        return
        
    latest_entry = feed.entries[0]
    item_title = latest_entry.get('title', 'No Title')
    print(f"\nProcessing the latest item: {item_title}")
    
    raw_content = ""
    if 'content' in latest_entry and latest_entry.content:
        raw_content = latest_entry.content[0].value
    elif 'summary' in latest_entry:
        raw_content = latest_entry.summary
    
    if not raw_content:
        print("  [Warning] No content found in this item. Exiting.")
        return
        
    post_to_wordpress_custom_api(config, item_title, raw_content)

    print("\n--- Script finished. ---")

if __name__ == "__main__":
    main()
