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

os.makedirs(POSTS_DIR, exist_ok=True)

def is_published(url):
    if not os.path.exists(DB_FILE): return False
    with open(DB_FILE, "r") as f:
        return url in f.read()

def mark_as_published(url):
    with open(DB_FILE, "a") as f:
        f.write(url + "\n")

def clean_text(text):
    """Удаляет технический мусор ИИ и лишнее форматирование"""
    # Убираем [Empty line], [blank line], фразы про формат и т.д.
    text = re.sub(r'\[.*?line\]|\[insert.*?\]|here is the.*?news:|specified format:', '', text, flags=re.IGNORECASE)
    # Убираем жирные звездочки
    text = text.replace("**", "").replace("##", "")
    return text.strip()

def ask_ai(title, summary):
    prompt = (
        f"Rewrite this tech news as a professional journalist.\n"
        f"Do not write any introductory phrases. Output ONLY the rewritten news.\n"
        f"Format:\n"
        f"Line 1: Catchy Title\n"
        f"Line 2+: Article body (3-4 paragraphs)\n\n"
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
    print("--- 🚀 Starting Text-Only News Bot ---")
    feed = feedparser.parse(RSS_URL)
    
    for entry in feed.entries[:5]:
        if is_published(entry.link): continue

        print(f"📝 Processing: {entry.title}")
        ai_response = ask_ai(entry.title, entry.summary)
        if not ai_response or len(ai_response) < 100: continue

        lines = ai_response.split('\n')
        ai_title = clean_text(lines[0])
        article_body = clean_text("\n".join(lines[1:]))

        timestamp = int(time.time())
        post_filename = os.path.join(POSTS_DIR, f"post_{timestamp}.md")

        with open(post_filename, "w", encoding="utf-8") as f:
            f.write('---\n')
            f.write(f'title: "{ai_title}"\n')
            f.write(f'date: {datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")}\n')
            f.write('draft: false\n')
            f.write('---\n\n')
            f.write(article_body)
            f.write(f"\n\n---\n*Source: [The Verge]({entry.link})*")

        mark_as_published(entry.link)
        print(f"✅ Success: {ai_title}")

if __name__ == "__main__":
    run_bot()
