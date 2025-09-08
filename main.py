import os
import requests
import feedparser
import google.generativeai as genai
import json
import base64
import hashlib
import time
from bs4 import BeautifulSoup

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
        'gemini_api_key': os.getenv('GEMINI_API_KEY'),
        'sources': json.loads(sources_json),
        # --- کلید اصلی فعال/غیرفعال ---
        # برای تست، این مقدار را False بگذارید.
        # برای استفاده نهایی، آن را به True تغییر دهید.
        'save_processed_links': False 
    }
    for key in ['wp_url', 'wp_user', 'wp_password', 'gemini_api_key']:
        if not config[key]:
            raise ValueError(f"خطا: متغیر محیطی {key.upper()} تعریف نشده است.")

    credentials = f"{config['wp_user']}:{config['wp_password']}"
    token = base64.b64encode(credentials.encode()).decode('utf-8')
    config['wp_headers'] = {
        'Authorization': f'Basic {token}',
        'Content-Type': 'application/json',
        'User-Agent': 'Python-News-Bot/Toggled'
    }
    
    print(f"[Info] Save Processed Links Mode: {config['save_processed_links']}")
    return config

# --- بخش ۲: مدیریت آیتم‌های تکراری (وابسته به کلید) ---
def get_processed_items_from_wp(config):
    if not config['save_processed_links']:
        print("[Info] Link saving is disabled. Skipping check for processed items.")
        return set()
        
    api_url = f"{config['wp_url']}/wp-json/my-poster/v1/processed-links"
    try:
        response = requests.get(api_url, headers=config['wp_headers'], timeout=60)
        response.raise_for_status()
        return set(response.json())
    except requests.exceptions.RequestException as e:
        print(f"[Fatal] Could not get processed links from WordPress: {e}")
        raise

def save_processed_item_to_wp(config, item_link):
    if not config['save_processed_links']:
        print(f"  -> [Info] Link saving is disabled. Skipping save for: {item_link}")
        return True

    api_url = f"{config['wp_url']}/wp-json/my-poster/v1/processed-links"
    payload = {"link": item_link}
    try:
        response = requests.post(api_url, headers=config['wp_headers'], json=payload, timeout=60)
        response.raise_for_status()
        print(f"  -> [Success] Saved processed link to WordPress.")
        return True
    except requests.exceptions.RequestException as e:
        print(f"  [Error] Failed to save processed link: {e}")
        return False

# --- (توابع دیگر بدون تغییر) ---
def extract_and_process_video(html_content):
    if not html_content: return "", ""
    soup = BeautifulSoup(html_content, 'html.parser')
    video_iframe = soup.find('iframe')
    if video_iframe:
        video_code = str(video_iframe)
        video_iframe.decompose()
        return video_code, str(soup)
    return "", html_content

def translate_with_gemini(api_key, title, content):
    print(f"  -> Translating: {title[:40]}...")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    prompt = f"""
    Translate the following HTML content and its title to fluent Persian.
    Preserve the original HTML structure. Return the output ONLY in JSON format
    with two keys: "translated_title" and "translated_content".
    Original Title: {title}
    Original HTML Content: {content}
    """
    try:
        response = model.generate_content(prompt)
        return json.loads(response.text.strip().replace('```json', '').replace('```', ''))
    except Exception as e:
        print(f"  [Error] Gemini API call failed: {e}")
        return None

def post_to_wordpress_custom_api(config, data, video_html):
    api_url = f"{config['wp_url']}/wp-json/my-poster/v1/create"
    slug = hashlib.sha1(data['translated_title'].encode('utf-8')).hexdigest()[:12]
    final_content = video_html + data['translated_content']
    post_data = {
        "title": data['translated_title'],
        "content": final_content,
        "slug": f"news-{slug}",
        "category_id": 80
    }
    try:
        response = requests.post(api_url, headers=config['wp_headers'], json=post_data, timeout=90)
        response.raise_for_status()
        print(f"  [Success] Post '{data['translated_title']}' created successfully.")
        return True
    except requests.exceptions.RequestException as e:
        print(f"  [Error] Failed to post to WordPress: {e}")
        if e.response: print(f"  [Debug] Response Body: {e.response.text}")
        return False

# --- بخش اصلی برنامه ---
def main():
    try:
        config = load_config()
    except Exception as e:
        print(f"[Fatal Error] {e}")
        return

    print("\n--- Starting News Aggregator Script ---")
    
    processed_items = get_processed_items_from_wp(config)
    
    for source in config['sources']:
        source_name = source['name']
        rss_url = source['rss_url']
        print(f"\n--- Processing Source: {source_name} ---")
        
        feed = feedparser.parse(rss_url)
        if feed.bozo:
            print(f"  [Warning] Error reading RSS feed: {feed.bozo_exception}")
            continue
            
        post_processed_in_this_run = False
        for entry in reversed(feed.entries):
            # اگر در حالت تست هستیم و یک پست پردازش شده، متوقف شو
            if not config['save_processed_links'] and post_processed_in_this_run:
                print("[Info] Test mode: Halting after one post.")
                break

            item_link = entry.get('link')
            item_title = entry.get('title', 'No Title')
            
            if not item_link or item_link in processed_items:
                continue
                
            print(f"\nProcessing new item: {item_title}")
            
            content_from_feed = ""
            if 'content' in entry and entry.content:
                content_from_feed = entry.content[0].value
            elif 'summary' in entry:
                content_from_feed = entry.summary
            
            if not content_from_feed:
                save_processed_item_to_wp(config, item_link)
                continue

            video_code, text_content_to_translate = extract_and_process_video(content_from_feed)
            translated_data = translate_with_gemini(config['gemini_api_key'], item_title, text_content_to_translate)
            
            if not translated_data:
                save_processed_item_to_wp(config, item_link)
                continue # به آیتم بعدی برو
                
            if post_to_wordpress_custom_api(config, translated_data, video_code):
                save_processed_item_to_wp(config, item_link)
            
            post_processed_in_this_run = True

    print("\n--- Script finished. ---")

if __name__ == "__main__":
    main()
