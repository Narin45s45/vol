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
        'User-Agent': 'Python-Final-Test-Bot/1.0'
    }
    return config

# --- بخش ۲: ارسال پست به وردپرس ---
def post_to_wordpress_custom_api(config, title, content):
    api_url = f"{config['wp_url']}/wp-json/my-poster/v1/create"
    slug = hashlib.sha1(title.encode('utf-8')).hexdigest()[:12]
    post_data = {
        "title": f"[Image Test] {title}",
        "content": content,
        "slug": f"image-test-{slug}",
        "category_id": 80
    }
    print(f"  -> [Info] Posting to WordPress: {title}")
    try:
        response = requests.post(api_url, headers=config['wp_headers'], json=post_data, timeout=90)
        response.raise_for_status()
        print(f"  [Success] Test post created successfully.")
        # در لاگ، لینک پست ایجاد شده را نمایش می‌دهیم
        print(f"  [Info] New Post URL: {response.json().get('url', 'N/A')}")
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

    print("\n--- Starting Image Extraction Test (No Translation, No BeautifulSoup) ---")
    
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
    
    text_content = latest_entry.get('summary', '')
    image_html = ""
    
    if 'media_thumbnail' in latest_entry and latest_entry.media_thumbnail:
        image_url = latest_entry.media_thumbnail[0].get('url')
        if image_url:
            # ساخت کد HTML عکس به صورت دستی
            image_html = f'<p><img src="{image_url}" alt="{item_title}" style="max-width:100%; height:auto;" /></p>'
            print(f"  [Info] Found and created HTML for media thumbnail: {image_url}")

    # ترکیب عکس و متن
    final_content = image_html + text_content
    
    post_to_wordpress_custom_api(config, item_title, final_content)

    print("\n--- Script finished. ---")

if __name__ == "__main__":
    main()
