import os
import requests
import feedparser
import google.generativeai as genai
import json
import base64
import hashlib

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
        # --- تغییر جدید: کلید به صورت ثابت در کد قرار گرفته ---
        'save_processed_links': False  # برای تست روی حالت False (ذخیره نکن)
    }
    for key in ['wp_url', 'wp_user', 'wp_password', 'gemini_api_key']:
        if not config[key]:
            raise ValueError(f"خطا: متغیر محیطی {key.upper()} تعریف نشده است.")

    credentials = f"{config['wp_user']}:{config['wp_password']}"
    token = base64.b64encode(credentials.encode()).decode('utf-8')
    config['wp_headers'] = {
        'Authorization': f'Basic {token}',
        'Content-Type': 'application/json',
        'User-Agent': 'Python-News-Bot/TestMode'
    }
    
    print(f"[Debug] Save Processed Links Mode: {config['save_processed_links']}")
    return config

# --- بخش ۲: مدیریت آیتم‌های تکراری ---
def get_processed_items_from_wp(config):
    if not config['save_processed_links']:
        print("[Debug] Link saving is disabled. Skipping check for processed links.")
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

# --- (بخش‌های ۳ و ۴ بدون تغییر باقی می‌مانند) ---
# --- بخش ۳: ترجمه با Gemini ---
def translate_with_gemini(api_key, title, content):
    print(f"  -> [Debug] Translating: {title[:40]}...")
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

# --- بخش ۴: ارسال پست به وردپرس ---
def post_to_wordpress_custom_api(config, data):
    api_url = f"{config['wp_url']}/wp-json/my-poster/v1/create"
    slug = hashlib.sha1(data['translated_title'].encode('utf-8')).hexdigest()[:12]

    post_data = {
        "title": data['translated_title'],
        "content": data['translated_content'],
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

# --- بخش ۵: منطق اصلی برنامه ---
def main():
    try:
        config = load_config()
    except Exception as e:
        print(f"[Fatal Error] {e}")
        return

    print("\n--- Starting Final News Aggregator Script (TEST MODE) ---")
    
    processed_items = get_processed_items_from_wp(config)
    
    for source in config['sources']:
        source_name = source['name']
        rss_url = source['rss_url']
        print(f"\n--- Processing Source: {source_name} ---")
        
        feed = feedparser.parse(rss_url)
        if feed.bozo:
            print(f"  [Warning] Error reading RSS feed: {feed.bozo_exception}")
            continue
            
        # --- تغییر جدید: فقط یک پست را پردازش کن و متوقف شو ---
        for entry in reversed(feed.entries):
            item_link = entry.get('link')
            item_title = entry.get('title', 'No Title')
            
            if not item_link or item_link in processed_items:
                continue
                
            print(f"\nProcessing the first new item found: {item_title}")
            
            content = ""
            if 'content' in entry and entry.content:
                content = entry.content[0].value
            elif 'summary' in entry:
                content = entry.summary
            
            if not content:
                print("  [Warning] No content found. Skipping.")
                save_processed_item_to_wp(config, item_link)
                # چون فقط یک آیتم را پردازش می‌کنیم، از حلقه خارج می‌شویم
                break

            translated_data = translate_with_gemini(config['gemini_api_key'], item_title, content)
            if not translated_data:
                save_processed_item_to_wp(config, item_link)
                # خروج از حلقه
                break
                
            if post_to_wordpress_custom_api(config, translated_data):
                save_processed_item_to_wp(config, item_link)
            
            # پس از پردازش موفق اولین آیتم جدید، از حلقه خارج شو
            print("[Debug] One post processed. Exiting loop as per test mode.")
            break

    print("\n--- Script finished. ---")

if __name__ == "__main__":
    main()
