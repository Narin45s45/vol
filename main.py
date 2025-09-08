import os
import requests
import feedparser
import json
import base64
import hashlib

# --- (بخش ۱: بارگذاری تنظیمات - بدون تغییر) ---
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
        'User-Agent': 'Python-Video-Embed-Bot/1.0'
    }
    return config

# --- بخش ۲: ارسال پست به وردپرس (بدون تغییر) ---
def post_to_wordpress_custom_api(config, title, content):
    api_url = f"{config['wp_url']}/wp-json/my-poster/v1/create"
    slug = hashlib.sha1(title.encode('utf-8')).hexdigest()[:12]
    post_data = {
        "title": f"[VIDEO] {title}",
        "content": content,
        "slug": f"video-{slug}",
        "category_id": 80
    }
    print(f"  -> [Info] Posting to WordPress: {title}")
    try:
        response = requests.post(api_url, headers=config['wp_headers'], json=post_data, timeout=90)
        response.raise_for_status()
        # پاسخ کامل را برمی‌گردانیم تا لینک در لاگ چاپ شود
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"  [Error] Failed to post to WordPress: {e}")
        if e.response: print(f"  [Debug] Response Body: {e.response.text}")
        return None

# --- بخش ۳: منطق اصلی برنامه (با تغییرات نهایی) ---
def main():
    try:
        config = load_config()
    except Exception as e:
        print(f"[Fatal Error] {e}")
        return

    print("\n--- Starting Video Embed Script (No Translation) ---")
    
    source = config['sources'][0]
    rss_url = source['rss_url']
    print(f"\n--- Processing Source: {source['name']} ---")
    
    feed = feedparser.parse(rss_url)
    if feed.bozo or not feed.entries:
        print("  [Warning] Feed is empty or could not be parsed.")
        return
        
    latest_entry = feed.entries[0]
    item_title = latest_entry.get('title', 'No Title')
    item_link = latest_entry.get('link')

    if not item_link:
        print("  [Error] No link found for the latest item. Cannot create embed.")
        return
        
    print(f"\nProcessing the latest item: {item_title}")
    
    # --- تغییر کلیدی: ساخت کد embed ویدیو از لینک اصلی ---
    video_html = ""
    if "ign.com/videos/" in item_link:
        # تبدیل لینک صفحه به لینک embed
        embed_url = item_link.replace("ign.com/videos/", "ign.com/embeds/videos/")
        # ساخت کد کامل iframe
        video_html = f'<div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; height: auto;"><iframe src="{embed_url}" width="100%" height="100%" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;" frameborder="0" scrolling="no" allowfullscreen="true"></iframe></div>'
        print(f"  [Info] Created video embed code for URL: {embed_url}")
    else:
        print("  [Warning] The link does not seem to be a standard IGN video link.")

    text_content = latest_entry.get('summary', '')
    
    # ترکیب ویدیو و متن
    final_content = video_html + f"<p>{text_content}</p>"
    
    post_response = post_to_wordpress_custom_api(config, item_title, final_content)

    # --- تغییر جدید: نمایش لینک پست وردپرس در لاگ ---
    if post_response and post_response.get("url"):
        print(f"  [SUCCESS] New WordPress Post URL: {post_response['url']}")

    print("\n--- Script finished. ---")

if __name__ == "__main__":
    main()
