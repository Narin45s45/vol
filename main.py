import os
import requests
import feedparser
import json
import base64
import hashlib
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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
    config['wp_headers'] = { 'Authorization': f'Basic {token}', 'Content-Type': 'application/json', 'User-Agent': 'Python-Selenium-Bot/2.0' }
    return config

# --- تابع استخراج ویدیو (با تغییر کوچک) ---
def get_video_embed_with_selenium(page_url):
    print(f"  -> Launching Selenium browser to scrape: {page_url}")
    video_html = ""
    
    options = ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36")

    try:
        # --- تغییر اصلی: دیگر نیازی به webdriver-manager نیست ---
        # Action گیت‌هاب درایور را به صورت خودکار در مسیر قرار می‌دهد
        driver = webdriver.Chrome(options=options)
        
        driver.get(page_url)
        
        wait = WebDriverWait(driver, 15) # زمان انتظار را کمی بیشتر می‌کنیم
        meta_tag = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "meta[property='og:video:url']"))
        )
        
        embed_url = meta_tag.get_attribute('content')
        if embed_url:
            print(f"  [Success] Found real video embed URL via Selenium: {embed_url}")
            video_html = f'<div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; height: auto;"><iframe src="{embed_url}" width="100%" height="100%" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;" frameborder="0" scrolling="no" allowfullscreen="true"></iframe></div>'
        
    except Exception as e:
        print(f"  [Error] Selenium failed to extract video embed: {e}")
    finally:
        if 'driver' in locals():
            driver.quit()
            
    return video_html

# --- (بقیه توابع و منطق اصلی برنامه بدون تغییر باقی می‌مانند) ---
def post_to_wordpress_custom_api(config, title, content):
    api_url = f"{config['wp_url']}/wp-json/my-poster/v1/create"
    slug = hashlib.sha1(title.encode('utf-8')).hexdigest()[:12]
    post_data = { "title": f"[VIDEO-Selenium] {title}", "content": content, "slug": f"video-selenium-{slug}", "category_id": 80 }
    print(f"  -> Posting to WordPress...")
    try:
        response = requests.post(api_url, headers=config['wp_headers'], json=post_data, timeout=90)
        response.raise_for_status()
        print(f"  [Success] Post created: {response.json().get('url', 'N/A')}")
        return True
    except requests.exceptions.RequestException as e:
        if e.response: print(f"  [Debug] Response Body: {e.response.text}"); return False

def main():
    try:
        config = load_config()
    except Exception as e:
        print(f"[Fatal Error] {e}"); return

    print("\n--- Starting Selenium Video Extractor Script (Optimized) ---")
    
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
    
    video_html = get_video_embed_with_selenium(item_link)
    
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
