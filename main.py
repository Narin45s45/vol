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
    config['wp_headers'] = { 'Authorization': f'Basic {token}', 'Content-Type': 'application/json', 'User-Agent': 'Python-Final-Bot/3.0' }
    return config

# --- تابع نهایی برای استخراج ویدیو از داده‌های JSON صفحه ---
def get_video_embed_from_page_data(page_url):
    """به صفحه وب مراجعه کرده، داده‌های JSON آن را تحلیل و لینک embed واقعی را استخراج می‌کند."""
    print(f"  -> Scraping page to find real embed URL from __NEXT_DATA__: {page_url}")
    video_html = ""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(page_url, headers=headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        next_data_script = soup.find('script', id='__NEXT_DATA__')
        if not next_data_script:
            print("  [Warning] '__NEXT_DATA__' script tag not found.")
            return ""

        page_data = json.loads(next_data_script.string)
        
        # --- تغییر کلیدی: به جای ساختن لینک، آن را مستقیماً از JSON می‌خوانیم ---
        # این مسیر دقیق بر اساس داده‌هایی است که شما فرستادید
        embed_url = page_data.get('props', {}).get('pageProps', {}).get('page', {}).get('schema', {}).get('embedUrl')
        
        if embed_url:
            print(f"  [SUCCESS] Found the REAL embed URL directly from JSON: {embed_url}")
            video_html = f'<div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; height: auto;"><iframe src="{embed_url}" width="100%" height="100%" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;" frameborder="0" scrolling="no" allowfullscreen="true"></iframe></div>'
        else:
            print("  [Warning] Could not find 'embedUrl' in the expected JSON path.")

    except Exception as e:
        print(f"  [Error] Failed to get video embed from page data: {e}")
    
    return video_html

# --- (بخش ارسال پست به وردپرس - بدون تغییر) ---
def post_to_wordpress_custom_api(config, title, content):
    api_url = f"{config['wp_url']}/wp-json/my-poster/v1/create"
    slug = hashlib.sha1(title.encode('utf-8')).hexdigest()[:12]
    post_data = { "title": f"[Final Video] {title}", "content": content, "slug": f"final-video-{slug}", "category_id": 80 }
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

    print("\n--- Starting Final Video Extractor Script (Corrected JSON Path) ---")
    source = config['sources'][0]
    item_link = feedparser.parse(source['rss_url']).entries[0].get('link')
    item_title = feedparser.parse(source['rss_url']).entries[0].get('title', 'No Title')
        
    print(f"\nProcessing the latest item: {item_title}")
    
    video_html = get_video_embed_from_page_data(item_link)
    
    if not video_html:
        latest_entry = feedparser.parse(source['rss_url']).entries[0]
        if 'media_thumbnail' in latest_entry and latest_entry.media_thumbnail:
            image_url = latest_entry.media_thumbnail[0].get('url')
            if image_url:
                print(f"  [Info] Fallback: Using media thumbnail from feed: {image_url}")
                video_html = f'<p><img src="{image_url}" alt="{item_title}" style="max-width:100%; height:auto;" /></p>'

    text_content = feedparser.parse(source['rss_url']).entries[0].get('summary', '')
    final_content = video_html + f"<p>{text_content}</p>"
    
    post_to_wordpress_custom_api(config, item_title, final_content)

    print("\n--- Script finished. ---")

if __name__ == "__main__":
    main()
