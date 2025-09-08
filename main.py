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
    config['wp_headers'] = { 'Authorization': f'Basic {token}', 'Content-Type': 'application/json', 'User-Agent': 'Python-FastAPI-Bot/2.0' }
    return config

# --- تابع جدید و سریع برای استخراج ویدیو از داده‌های JSON صفحه ---
def get_video_embed_from_page_data(page_url):
    """به صفحه وب مراجعه کرده، داده‌های JSON آن را تحلیل و لینک embed را استخراج می‌کند."""
    print(f"  -> Scraping page to find video data from JSON: {page_url}")
    video_html = ""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(page_url, headers=headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # ۱. پیدا کردن تگ اسکریپت که حاوی تمام داده‌های صفحه است
        next_data_script = soup.find('script', id='__NEXT_DATA__')
        
        if not next_data_script:
            print("  [Warning] '__NEXT_DATA__' script tag not found. This is the main issue.")
            return ""

        # ۲. تبدیل محتوای تگ به JSON
        page_data = json.loads(next_data_script.string)
        
        # ۳. جستجو در ساختار JSON برای پیدا کردن ID ویدیو
        video_id = ""
        # این ساختار پیچیده است، اما ما به دنبال کلید 'video' در داده‌های صفحه می‌گردیم
        apollo_state = page_data.get('props', {}).get('pageProps', {}).get('apolloState', {})
        for key, value in apollo_state.items():
            if isinstance(value, dict) and value.get('__typename') == 'Video' and 'id' in value:
                video_id = value['id']
                break
        
        if video_id:
            print(f"  [Success] Found video ID from page JSON: {video_id}")
            embed_url = f"https://www.ign.com/videos/embed?id={video_id}"
            video_html = f'<div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; height: auto;"><iframe src="{embed_url}" width="100%" height="100%" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;" frameborder="0" scrolling="no" allowfullscreen="true"></iframe></div>'
        else:
            print("  [Warning] Could not find video ID within the page's JSON data.")

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

    print("\n--- Starting Fast Video Extractor Script (JSON Method) ---")
    
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
    
    # استخراج ویدیو با روش جدید و پایدار (تحلیل JSON)
    video_html = get_video_embed_from_page_data(item_link)
    
    # اگر روش اصلی شکست خورد، از عکس بندانگشتی استفاده کن
    if not video_html and 'media_thumbnail' in latest_entry and latest_entry.media_thumbnail:
        image_url = latest_entry.media_thumbnail[0].get('url')
        if image_url:
            print(f"  [Info] Fallback: Using media thumbnail from feed: {image_url}")
            video_html = f'<p><img src="{image_url}" alt="{item_title}" style="max-width:100%; height:auto;" /></p>'

    text_content = latest_entry.get('summary', '')
    final_content = video_html + f"<p>{text_content}</p>"
    
    post_to_wordpress_custom_api(config, item_title, final_content)

    print("\n--- Script finished. ---")

if __name__ == "__main__":
    main()
