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
    sources_json = os.getenv('SOURCES_CONFIG')
    if not sources_json:
        raise ValueError("خطا: متغیر محیطی SOURCES_CONFIG تعریف نشده است.")
    config = {
        'wp_url': os.getenv('WP_URL'),
        'wp_user': os.getenv('WP_USER'),
        'wp_password': os.getenv('WP_PASSWORD'),
        'gemini_api_key': os.getenv('GEMINI_API_KEY'),
        'sources': json.loads(sources_json),
        # --- تغییر اصلی: ذخیره‌سازی به صورت ثابت غیرفعال شده است ---
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
        'User-Agent': 'Python-News-Bot/Final-Test'
    }
    print(f"[Debug] Save Processed Links Mode: {config['save_processed_links']}")
    return config

# --- بخش ۲: مدیریت آیتم‌های تکراری ---
def get_processed_items_from_wp(config):
    # --- تغییر اصلی: اگر ذخیره‌سازی غیرفعال باشد، همیشه لیست خالی برمی‌گرداند ---
    if not config['save_processed_links']:
        print("[Debug] Link saving is disabled. Returning empty list for processed items.")
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
    # --- تغییر اصلی: اگر ذخیره‌سازی غیرفعال باشد، هیچ کاری انجام نمی‌دهد ---
    if not config['save_processed_links']:
        print(f"  -> [Debug] Link saving is disabled. Skipping save for: {item_link}")
        return True

    api_url = f"{config['wp_url']}/wp-json/my-poster/v1/processed-links"
    payload = {"link": item_link}
    try:
        response = requests.post(api_url, headers=config['wp_headers'], json=payload, timeout=60)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"  [Error] Failed to save processed link to WordPress: {e}")
        return False

# --- (سایر توابع مانند ترجمه و ارسال پست بدون تغییر باقی می‌مانند) ---
def extract_and_process_video(html_content):
    if not html_content: return "", ""
    soup = BeautifulSoup(html_content, 'html.parser')
    video_iframe = soup.find('iframe')
    if video_iframe:
        video_code = str(video_iframe)
        video_iframe.decompose()
        print("  [Debug] Found and extracted an iframe video embed.")
        return video_code, str(soup)
    print("  [Debug] No video iframe found in the content.")
    return "", html_content

def translate_with_gemini(api_key, title, content):
    print(f"  -> [Debug] Translating: {title[:40]}...")
    genai.configure(api_e, 'application/json'}
    try:
        response = requests.post(api_url, headers=headers, json=post_data, timeout=90)
        response.raise_for_status()
        print(f"  [Success] Post '{data['translated_title']}' created successfully.")
        return True
    except requests.exceptions.RequestException as e:
        print(f"  [Error] Failed to post to WordPress: {e}")
        if e.response: print(f"  [Debug] Response Body: {e.response.text}")
        return False

# --- بخش ۵: منطق اصلی برنامه ---
def main():
    try:
        config = load_config()
    except Exception as e:
        print(f"[Fatal Error] {e}")
        return

    print("\n--- Starting News Aggregator Script (TEST MODE - SAVING DISABLED) ---")
    
    processed_items = get_processed_items_from_wp(config)
    
    for source in config['sources']:
        source_name = source['name']
        rss_url = source['rss_url']
        print(f"\n--- Processing Source: {source_name} ---")
        
        feed = feedparser.parse(rss_url)
        if feed.bozo:
            print(f"  [Warning] Error reading RSS feed: {feed.bozo_exception}")
            continue
            
        # فقط اولین آیتم جدید در فید را پردازش می‌کند و متوقف می‌شود
        for entry in reversed(feed.entries):
            item_link = entry.get('link')
            item_title = entry.get('title', 'No Title')
            
            if not item_link or item_link in processed_items:
                continue
                
            print(f"\nProcessing the first new item found: {item_title}")
            
            content_from_feed = ""
            if 'content' in entry and entry.content:
                content_from_feed = entry.content[0].value
            elif 'summary' in entry:
                content_from_feed = entry.summary
            
            if not content_from_feed:
                print("  [Warning] No content found. Skipping.")
                save_processed_item_to_wp(config, item_link)
                break

            video_code, text_content_to_translate = extract_and_process_video(content_from_feed)

            translated_data = translate_with_gemini(config['gemini_api_key'], item_title, text_content_to_translate)
            if not translated_data:
                save_processed_item_to_wp(config, item_link)
                break
                
            if post_to_wordpress_custom_api(config, translated_data, video_code):
                save_processed_item_to_wp(config, item_link)
            
            print("\n[Debug] Halting after one item for testing.")
            break # <-- مهم: پس از پردازش یک آیتم، حلقه متوقف می‌شود

    print("\n--- Script finished. ---")

if __name__ == "__main__":
    main()
