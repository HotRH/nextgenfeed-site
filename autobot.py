import feedparser
import os
import subprocess
import time
import requests
from datetime import datetime

# --- КОНФИГУРАЦИЯ ---
RSS_URL = "https://www.theverge.com/rss/index.xml" 
DB_FILE = "published_urls.txt"
POSTS_DIR = "content/posts"
IMAGES_DIR = "static/images"

os.makedirs(POSTS_DIR, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)

def is_published(url):
    if not os.path.exists(DB_FILE): return False
    with open(DB_FILE, "r") as f:
        return url in f.read()

def mark_as_published(url):
    with open(DB_FILE, "a") as f:
        f.write(url + "\n")

def ask_ai(title, summary):
    prompt = (
        f"Act as a pro tech blogger. Rewrite this news for a global audience.\n"
        f"Strict Format:\n"
        f"Line 1: High-quality SEO Title\n"
        f"Line 2: One specific English keyword for image search (e.g. 'smartphone', 'ai', 'tesla')\n"
        f"Line 3: [Empty line]\n"
        f"Line 4+: Article body (3-4 paragraphs)\n\n"
        f"Original Title: {title}\nSummary: {summary}"
    )
    try:
        result = subprocess.run(
            ["ollama", "run", "llama3", prompt],
            capture_output=True, text=True, encoding="utf-8", check=True, timeout=180
        )
        return result.stdout.strip()
    except Exception as e:
        print(f"❌ AI Error: {e}")
        return None

def download_image(keyword, filename):
    url = f"https://loremflickr.com/1200/630/{keyword},tech/all"
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            with open(os.path.join(IMAGES_DIR, filename), 'wb') as f:
                f.write(response.content)
            return True
    except Exception as e:
        print(f"❌ Download Error: {e}")
    return False

def run_bot():
    print("--- 🚀 Starting High-Quality Content Bot ---")
    feed = feedparser.parse(RSS_URL)
    
    for entry in feed.entries[:5]:
        if is_published(entry.link): continue

        print(f"📝 Processing: {entry.title}")
        ai_response = ask_ai(entry.title, entry.summary)
        if not ai_response or len(ai_response) < 150: continue

        lines = ai_response.split('\n')
        ai_title = lines[0].strip().replace('"', "'")
        raw_keyword = lines[1].strip().lower() if len(lines) > 1 else "technology"
        photo_keyword = "".join(x for x in raw_keyword if x.isalnum())
        
        article_body = '\n'.join(lines[3:]).strip()
        timestamp = int(time.time())
        img_filename = f"img_{timestamp}.jpg"
        
        if download_image(photo_keyword, img_filename):
            final_image_url = f"/images/{img_filename}"
        else:
            final_image_url = "https://loremflickr.com/1200/630/tech"

        post_filename = os.path.join(POSTS_DIR, f"post_{timestamp}.md")
        with open(post_filename, "w", encoding="utf-8") as f:
            f.write('---\n')
            f.write(f'title: "{ai_title}"\n')
            f.write(f'date: {datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")}\n')
            f.write(f'image: "{final_image_url}"\n')
            f.write('draft: false\n')
            f.write('---\n\n')
            f.write(f'![{ai_title}]({final_image_url})\n\n')
            f.write(article_body)
            f.write(f"\n\n---\n*Source: [The Verge]({entry.link})*")

        mark_as_published(entry.link)
        print(f"✅ Success: {post_filename}")

if __name__ == "__main__":
    run_bot()
