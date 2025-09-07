import os
import requests
import feedparser
import google.generativeai as genai
import json

# --- بخش ۱: بارگذاری تنظیمات ---
def load_config():
    # [دیباگ] اضافه شده
    print("[Debug] Loading configuration from environment variables...")
    sources_json = os.getenv('SOURCES_CONFIG')
    if not sources_json:
        raise ValueError("خطا: متغیر محیطی SOURCES_CONFIG تعریف نشده است.")
    
    config = {
        'wp_url': os.getenv('WP_URL'),
        'wp_user': os.getenv('WP_USER'),
        'wp_password': os.getenv('WP_PASSWORD'),
        'gemini_api_key': os.getenv('GEMINI_API_KEY'),
        'post_status': 'publish',
        'sources': json.loads(sources_json)
    }
    for key in ['wp_url', 'wp_user', 'wp_password', 'gemini_api_key']:
        if not config[key]:
            raise ValueError(f"خطا: متغیر محیطی {key} تعریف نشده است.")
    print("[Debug] Configuration loaded successfully.")
    return config

# --- بخش ۲: مدیریت آیتم‌های تکراری ---
PROCESSED_ITEMS_FILE = 'processed_items.txt'

def get_processed_items():
    if not os.path.exists(PROCESSED_ITEMS_FILE):
        return set()
    with open(PROCESSED_ITEMS_FILE, 'r', encoding='utf-8') as f:
        return set(line.strip() for line in f)

def save_processed_item(item_link):
    with open(PROCESSED_ITEMS_FILE, 'a', encoding='utf-8') as f:
        f.write(item_link + '\n')

# --- بخش ۳: ترجمه با Gemini ---
def translate_content_with_gemini(api_key, title, html_content):
    print(f"  -> [Debug] Sending to Gemini for translation: {title[:30]}...")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    prompt = f"""
    Translate the following HTML content and its title to fluent Persian.
    Preserve the original HTML structure. Return the output ONLY in JSON format 
    with two keys: "translated_title" and "translated_content".
    Original Title: {title}
    Original HTML Content: {html_content}
    """
    try:
        response = model.generate_content(prompt)
        print("  -> [Debug] Received response from Gemini.")
        return json.loads(response.text.strip().replace('```json', '').replace('```', ''))
    except Exception as e:
        print(f"  [Error] Gemini API call failed: {e}")
        return None

# --- بخش ۴: مدیریت وردپرس ---
def get_or_create_category_id(config, auth, category_name, category_slug):
    cat_api_url = f"{config['wp_url']}/wp-json/wp/v2/categories"
    
    # [دیباگ] اضافه شده
    print(f"[Debug] Checking for category '{category_slug}' at {cat_api_url}")
    try:
        response = requests.get(cat_api_url, params={'slug': category_slug}, auth=auth, timeout=20)
        response.raise_for_status()
        data = response.json()
        if data:
            cat_id = data[0]['id']
            print(f"  [Debug] Category '{category_slug}' found with ID: {cat_id}")
            return cat_id
    except requests.exceptions.RequestException as e:
        print(f"  [Warning] Could not check for category, will try to create. Reason: {e}")

    print(f"  [Debug] Category '{category_slug}' not found or check failed. Attempting to create...")
    try:
        response = requests.post(cat_api_url, auth=auth, json={'name': category_name, 'slug': category_slug}, timeout=20)
        response.raise_for_status()
        cat_id = response.json()['id']
        print(f"  [Success] Category '{category_slug}' created with ID: {cat_id}")
        return cat_id
    except requests.exceptions.RequestException as e:
        print(f"  [Error] Failed to create category '{category_slug}': {e}")
        if e.response: print(f"  [Debug] Response Body: {e.response.text}")
        return None

def post_to_wordpress(config, auth, data, category_id):
    api_url = f"{config['wp_url']}/wp-json/wp/v2/posts"
    
    post_data = {
        'title': data['translated_title'],
        'content': data['translated_content'],
        'status': config['post_status'],
        'categories': [category_id]
    }
    
    headers = {'Content-Type': 'application/json'}
    
    # [دیباگ] اضافه شده
    print(f"  -> [Debug] Attempting to POST to WordPress: {data['translated_title'][:30]}...")
    try:
        response = requests.post(api_url, auth=auth, headers=headers, json=post_data, timeout=30)
        response.raise_for_status()
        print(f"  [Success] Post created successfully in WordPress.")
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
        print(e)
        return

    print("\n--- Starting Multi-Source Feed Translator Script (Debug Mode) ---")
    
    auth = (config['wp_user'], config['wp_password'])
    
    # [دیباگ] اضافه شده
    print("\n[Phase 1: Category Setup]")
    game_category_id = get_or_create_category_id(config, auth, 'بازی', 'game')
    if not game_category_id:
        print("[Fatal] Could not secure 'game' category ID. Aborting.")
        return
    print("[Phase 1: Complete]\n")

    processed_items = get_processed_items()
    
    print("[Phase 2: Processing Feeds]")
    for source in config['sources']:
        source_name = source['name']
        rss_url = source['rss_url']
        print(f"\n--- Processing Source: {source_name} ---")
        
        # [دیباگ] اضافه شده
        print(f"[Debug] Fetching RSS feed from: {rss_url}")
        feed = feedparser.parse(rss_url)
        if feed.bozo:
            print(f"  [Warning] Error reading RSS feed: {feed.bozo_exception}")
            continue
        print(f"[Debug] Found {len(feed.entries)} items in the feed.")
            
        for entry in reversed(feed.entries):
            item_link = entry.get('link')
            item_title = entry.get('title', 'No Title')
            
            if not item_link or item_link in processed_items:
                continue
                
            print(f"\nProcessing new item: {item_title}")
            
            content = entry.get('content', [{}])[0].get('value', entry.get('summary', ''))
            if not content:
                print("  [Warning] No content found. Skipping.")
                save_processed_item(item_link)
                continue

            translated_data = translate_content_with_gemini(config['gemini_api_key'], item_title, content)
            if not translated_data:
                save_processed_item(item_link)
                continue
                
            if post_to_wordpress(config, auth, translated_data, game_category_id):
                save_processed_item(item_link)

    print("\n[Phase 2: Complete]")
    print("\n--- Script finished. ---")

if __name__ == "__main__":
    main()
