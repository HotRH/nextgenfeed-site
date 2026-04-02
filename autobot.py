import feedparser
import os
import subprocess
import time
from datetime import datetime
import re

# --- КОНФИГУРАЦИЯ ---
RSS_URL = "https://www.theverge.com/rss/index.xml" 
DB_FILE = "published_urls.txt"
POSTS_DIR = "content/posts"

# Создаем папку для постов, если её нет
os.makedirs(POSTS_DIR, exist_ok=True)

def clean_text(text):
    """Удаляет технический мусор ИИ, лишнее форматирование и спецсимволы"""
    # Убираем [Empty line], [blank line], фразы про формат и "Here is the news"
    text = re.sub(r'\[.*?line\]|\[insert.*?\]|here is the.*?news:|specified format:|rewritten news:', '', text, flags=re.IGNORECASE)
    # Убираем жирные звездочки, решетки и обратные кавычки
    text = text.replace("**", "").replace("##", "").replace("`", "")
    return text.strip()

def ask_ai(title, summary):
    """Запрос к Ollama (Llama 3)"""
    prompt = (
        f"Rewrite this tech news as a professional journalist.\n"
        f"Output ONLY the title on the first line and the article starting from the second line.\n"
        f"Do NOT use any quotation marks in the title. Do NOT use markdown symbols like **.\n\n"
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

def run_bot():
    print("--- 🚀 Starting Bulletproof Text-Only Bot ---")
    
    # Загружаем ленту новостей
    feed = feedparser.parse(RSS_URL)
    
    # Проверяем файл базы данных
    if not os.path.exists(DB_FILE):
        open(DB_FILE, 'w').close()

    for entry in feed.entries[:5]:
        # Проверяем, не публиковали ли мы это раньше
        with open(DB_FILE, "r") as f:
            if entry.link in f.read():
                continue

        print(f"📝 Processing: {entry.title}")
        ai_response = ask_ai(entry.title, entry.summary)
        
        if not ai_response or len(ai_response) < 100:
            continue

        lines = ai_response.split('\n')
        
        # --- ОЧИСТКА ЗАГОЛОВКА (Решаем проблему Exit Code 1) ---
        raw_title = clean_text(lines[0])
        # Удаляем кавычки по краям и заменяем внутренние двойные на одинарные
        ai_title = raw_title.strip('"').strip("'").replace('"', "'")
        
        # --- СБОРКА ТЕКСТА ---
        article_body = clean_text("\n".join(lines[1:]))

        # Генерируем уникальное имя файла
        timestamp = int(time.time())
        post_filename = os.path.join(POSTS_DIR, f"post_{timestamp}.md")

        # Записываем файл в формате Hugo
        with open(post_filename, "w", encoding="utf-8") as f:
            f.write('---\n')
            f.write(f'title: "{ai_title}"\n') # Кавычки теперь только внешние, Hugo будет доволен
            f.write(f'date: {datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")}\n')
            f.write('draft: false\n')
            f.write('---\n\n')
            f.write(article_body)
            f.write(f"\n\n---\n*Source: [The Verge]({entry.link})*")

        # Помечаем как опубликованное
        with open(DB_FILE, "a") as f:
            f.write(entry.link + "\n")
            
        print(f"✅ Created: {ai_title}")

if __name__ == "__main__":
    run_bot()
