import feedparser
import os
import subprocess
import time
from datetime import datetime

# --- КОНФИГУРАЦИЯ ---
RSS_URL = "https://www.theverge.com/rss/index.xml" 
DB_FILE = "published_urls.txt"
POSTS_DIR = "content/posts"

# Создаем папку, если ее нет
os.makedirs(POSTS_DIR, exist_ok=True)

def is_published(url):
    if not os.path.exists(DB_FILE): return False
    with open(DB_FILE, "r") as f:
        return url in f.read()

def mark_as_published(url):
    with open(DB_FILE, "a") as f:
        f.write(url + "\n")

def ask_ai(title, summary):
    """Улучшенный промпт для SEO и качественного рерайта"""
    prompt = (
        f"You are an expert tech journalist. Rewrite this news for a global tech site.\n"
        f"Requirements:\n"
        f"1. Create a magnetic, clickable title (SEO friendly).\n"
        f"2. Write at least 3-4 detailed paragraphs.\n"
        f"3. Use professional and engaging tone.\n"
        f"4. Format: Title on the first line, then a blank line, then the article body.\n\n"
        f"Original Title: {title}\n"
        f"Original Summary: {summary}"
    )

    try:
        # Запускаем Ollama с таймаутом (чтобы бот не завис навсегда)
        result = subprocess.run(
            ["ollama", "run", "llama3", prompt],
            capture_output=True, text=True, encoding="utf-8", check=True, timeout=180
        )
        return result.stdout.strip()
    except Exception as e:
        print(f"❌ AI Error: {e}")
        return None

def run_bot():
    print("--- 🚀 Starting Professional AutoBot ---")
    
    # Инициализируем ленту (ЭТОЙ СТРОЧКИ НЕ ХВАТАЛО!)
    feed = feedparser.parse(RSS_URL)

    for entry in feed.entries[:5]:
        if is_published(entry.link):
            print(f"⏩ Skipping: {entry.title}")
            continue

        print(f"✍️ Writing: {entry.title}...")
        ai_response = ask_ai(entry.title, entry.summary)

        # Жесткая проверка: если AI выдал мало текста или ошибку - пропускаем
        if not ai_response or len(ai_response) < 200:
            print("⚠️ Skipping due to AI quality/error.")
            continue

        # Парсим заголовок и тело
        lines = ai_response.split('\n', 1)
        ai_title = lines[0].strip().replace('"', "'")
        article_body = lines[1].strip() if len(lines) > 1 else ai_response

        # Имя файла на основе времени (чтобы не было конфликтов)
        timestamp = int(time.time())
        filename = os.path.join(POSTS_DIR, f"post_{timestamp}.md")

        # КАРТИНКА: Используем LoremFlickr (намного стабильнее)
        # Берем первое слово заголовка как тему
        keyword = ai_title.split()[0].lower()
        image_url = f"https://loremflickr.com/1200/630/technology,{keyword}"

        # Записываем файл для Hugo с правильными SEO-тегами
        with open(filename, "w", encoding="utf-8") as f:
            f.write('---\n')
            f.write(f'title: "{ai_title}"\n')
            f.write(f'date: {datetime.now().strftime("%Y-%m-%dT%H:%M:%S+03:00")}\n')
            f.write(f'image: "{image_url}"\n')
            f.write('categories: ["Technology", "News"]\n')
            f.write('draft: false\n')
            f.write('---\n\n')
            f.write(f'![{ai_title}]({image_url})\n\n')
            f.write(article_body)
            f.write(f"\n\n---\n*Original source: [The Verge]({entry.link})*")

        mark_as_published(entry.link)
        print(f"✅ Published: {ai_title}")

if __name__ == "__main__":
    run_bot()
    print("--- ✨ All done! ---")
