import feedparser
import os
import subprocess
import time
import requests
import re
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

def clean_content(text):
    """Удаляет мусорные фразы ИИ и лишнее форматирование"""
    # Убираем [Empty line], [blank line] и прочее
    text = re.sub(r'\[.*?line\]|\[insert.*?\]', '', text, flags=re.IGNORECASE)
    # Убираем жирные звездочки и решетки
    text = text.replace("**", "").replace("##", "")
    return text.strip()

def ask_ai(title, summary):
    prompt = (
        f"Rewrite this tech news for a professional website.\n"
        f"STRICT FORMAT:\n"
        f"Line 1: Catchy Title (plain text only)\n"
        f"Line 2: One specific English word for image search (e.g. 'ai', 'gadget', 'space')\n"
        f"Line 3: [Blank]\n"
        f"Line 4+: Article text (3-4 paragraphs)\n\n"
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
    # Добавляем 'tech' к поиску для точности
    url = f"https://loremflickr.com/1200/800/{keyword},technology/all"
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            with open(os.path.join(IMAGES_DIR, filename), 'wb') as f:
                f.write(response.content)
            return True
    except Exception as e:
        print(f"❌ Image Error: {e}")
    return False

def run_bot():
    print("--- 🚀 Starting Super Clean Bot ---")
    feed = feedparser.parse(RSS_URL)
    
    for entry in feed.entries[:5]:
        if is_published(entry.link): continue

        print(f"📝 Processing: {entry.title}")
        ai_response = ask_ai(entry.title, entry.summary)
        if not ai_response or len(ai_response) < 100: continue

        lines = ai_response.split('\n')
        
        # 1. Заголовок (чистый)
        ai_title = clean_content(lines[0])
        
        # 2. Ключевое слово для фото
        raw_keyword = lines[1].strip().lower() if len(lines) > 1 else "tech"
        photo_keyword = re.sub(r'[^a-zA-Z]', '', raw_keyword)
        
        # 3. Тело статьи (без картинки внутри!)
        # Берем всё, что после 2-й строки и чистим
        article_body = clean_content("\n".join(lines[2:]))

        timestamp = int(time.time())
        img_filename = f"img_{timestamp}.jpg"
        
        if download_image(photo_keyword, img_filename):
            final_image_url = f"/images/{img_filename}"
        else:
            final_image_url = "https://loremflickr.com/1200/800/tech"

        post_filename = os.path.join(POSTS_DIR, f"post_{timestamp}.md")
        with open(post_filename, "w", encoding="utf-8") as f:
            f.write('---\n')
            f.write(f'title: "{ai_title}"\n')
            f.write(f'date: {datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")}\n')
            f.write(f'thumbnail: "{final_image_url}"\n') # Для главной страницы
            f.write(f'image: "{final_image_url}"\n')     # Для шапки статьи
            f.write('draft: false\n')
            f.write('---\n\n')
            # Сразу пишем текст, без тега ![]()
            f.write(article_body)
            f.write(f"\n\n---\n*Source: [The Verge]({entry.link})*")

        mark_as_published(entry.link)
        print(f"✅ Success: {ai_title}")

if __name__ == "__main__":
    run_bot()
