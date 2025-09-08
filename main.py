import os
import requests
import feedparser
import google.generativeai as genai
import json
import base64
import hashlib
import time
from bs4 import BeautifulSoup

# --- (بخش ۱: بارگذاری تنظیمات - بدون تغییر) ---
def load_config():
    sources_json = os.getenv('SOURCES_CONFIG')
    if not sources_json:
        raise ValueError("خطا: متغیر محیطی SOURCES_CONFIG تعریف نشده است.")
    config = {
        'wp_url': os.getenv('WP_URL'),
        'wp_user': os.getenv('WP_USER'),
        'wp_password': os.getenv('WP_PASSWORD'),
        'gemini_api_key': os.getenv('GEMINI_API_KEY'),
        'sources': json.loads(sources_json)
    }
    for key in ['wp_url', 'wp_user', 'wp_password', 'gemini_api_key']:
        if not config[key]:
            raise ValueError(f"خطا: متغیر محیطی {key.upper()} تعریف نشده است.")
    credentials = f"{config['wp_user']}:{config['wp_password']}"
    token = base64.b64encode(credentials.encode()).decode('utf-8')
    config['wp_headers'] = {
        'Authorization': f'Basic {token}',
        'Content-Type': 'application/json',
        'User-Agent': 'Python-News-Bot/Final'
    }
    print("[Debug] Configuration and Auth Headers loaded successfully.")
    return config

# --- (بخش ۲: مدیریت آیتم‌های تکراری - بدون تغییر) ---
def get_processed_items_from_wp(config):
    api_url = f"{config['wp_url']}/wp-json/my-poster/v1/processed-links"
    print(f"[Debug] Getting processed links from: {api_url}")
    try:
        response = requests.get(api_url, headers=config['wp_headers'], timeout=60)
        response.raise_for_status()
        return set(response.json())
    except requests.exceptions.RequestException as e:
        print(f"[Fatal] Could not get processed links from WordPress: {e}")
        raise

def save_processed_item_to_wp(config, item_link):
    api_url = f"{config['wp_url']}/wp-json/my-poster/v1/processed-links"
    payload = {"link": item_link}
    print(f"  -> [Debug] Saving processed link to WordPress: {item_link}")
    try:
        response = requests.post(api_url, headers=config['wp_headers'], json=payload, timeout=60)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"  [Error] Failed to save processed link to WordPress: {e}")
        return False

# --- تابع جدید برای پردازش هوشمند ویدیو ---
def extract_and_process_video(html_content):
    """
    کد ویدیو را پیدا کرده، آن را از متن اصلی جدا می‌کند و متن تمیز شده را برمی‌گرداند.
    """
    if not html_content:
        return "", ""
        
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # اول به دنبال iframe می‌گردیم (برای ویدیوهای Embed)
    video_iframe = soup.find('iframe')
    if video_iframe:
        video_code = str(video_iframe)
        video_iframe.decompose() # iframe را از متن اصلی حذف می‌کنیم
        print("  [Debug] Found and extracted an iframe video embed.")
        return video_code, str(soup)

    # اگر iframe نبود، به دنبال تگ ویدیو می‌گردیم
    video_tag = soup.find('video')
    if video_tag:
        video_code = str(video_tag)
        video_tag.decompose() # تگ ویدیو را از متن اصلی حذف می‌کنیم
        print("  [Debug] Found and extracted a <video> tag.")
        return video_code, str(soup)
        
    print("  [Debug] No video iframe or tag found in the content.")
    return "", html_content # اگر ویدیویی پیدا نشد، متن اصلی را برمی‌گردانیم

# --- بخش ۳: ترجمه با Gemini (بدون تغییر) ---
def translate_with_gemini(api_key, title, content):
    print(f"  -> [Debug] Translating: {title[:40]}...")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    prompt = f"""
    Translate the following HTML content and its title to fluent Persian.
    Preserve the original HTML structure as much as possible, but remove any remaining script tags.
    Return the output ONLY in JSON format with two keys: "translated_title" and "translated_content".
    Original Title: {title}
    Original HTML Content: {content}
    """
    try:
        response = model.generate_content(prompt)
        return json.loads(response.text.strip().replace('```json', '').replace('```', ''))
    except Exception as e:
        print(f"  [Error] Gemini API call failed: {e}")
        return None

# --- بخش ۴: ارسال پست به وردپرس (با تغییر) ---
def post_to_wordpress_custom_api(config, data, video_html):
    api_url = f"{config['wp_url']}/wp-json/my-poster/v1/create"
    slug = hashlib.sha1(data['translated_title'].encode('utf-8')).hexdigest()[:12]

    # --- تغییر جدید: کد ویدیو را به ابتدای محتوای ترجمه شده اضافه می‌کنیم ---
    final_content = video_html + data['translated_content']

    post_data = {
        "title": data['translated_title'],
        "content": final_content,
        "slug": f"news-{slug}",
        "category_id": 80
    }
    
    print(f"  -> [Debug] Posting to custom API endpoint...")
    try:
        response = requests.post(api_url, headers=config['wp_headers'], json=post_data, timeout=90)
        response.raise_for_status()
        print(f"  [Success] Post '{data['translated_title']}' created successfully.")
        return True
    except requests.exceptions.RequestException as e:
        print(f"  [Error] Failed to post to WordPress: {e}")
        if e.response: print(f"  [Debug] Response Body: {e.response.text}")
        return False

# --- بخش ۵: منطق اصلی برنامه (با تغییر) ---
def main():
    try:
        config = load_config()
    except Exception as e:
        print(f"[Fatal Error] {e}")
        return

    print("\n--- Starting Final News Aggregator Script ---")
    
    processed_items = get_processed_items_from_wp(config)
    print(f"Loaded {len(processed_items)} processed links from WordPress.")
    
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
            
            content_from_feed = ""
            if 'content' in entry and entry.content:
                content_from_feed = entry.content[0].value
            elif 'summary' in entry:
                content_from_feed = entry.summary
            
            if not content_from_feed:
                print("  [Warning] No content found. Skipping.")
                save_processed_item_to_wp(config, item_link)
                continue
            
            # --- تغییر جدید: استخراج ویدیو قبل از ترجمه ---
            video_code, text_content_to_translate = extract_and_process_video(content_from_feed)

            translated_data = translate_with_gemini(config['gemini_api_key'], item_title, text_content_to_translate)
            if not translated_data:
                save_processed_item_to_wp(config, item_link)
                continue
                
            if post_to_wordpress_custom_api(config, translated_data, video_code):
                save_processed_item_to_wp(config, item_link)

            time.sleep(5)

    print("\n--- Script finished. ---")

if __name__ == "__main__":
    main()
