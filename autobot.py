import feedparser
import os
import subprocess
import time
from datetime import datetime
import re
import trafilatura

# --- КОНФИГУРАЦИЯ ИСТОЧНИКОВ ---
RSS_SOURCES = [
    "https://www.theverge.com/rss/index.xml",
    "https://techcrunch.com/feed/",
    "https://arstechnica.com/feed/",
    "https://www.wired.com/feed/rss",
    "https://9to5google.com/feed/"
]

DB_FILE = "published_urls.txt"
POSTS_DIR = "content/posts"

os.makedirs(POSTS_DIR, exist_ok=True)

def get_full_text(url):
    """Выкачивает всю статью, отсекая мусор"""
    downloaded = trafilatura.fetch_url(url)
    if downloaded:
        return trafilatura.extract(downloaded, include_comments=False, include_tables=True)
    return None

def clean_text(text):
    """Удаляет артефакты ИИ"""
    text = re.sub(r'(?i)here is the.*?article:|rewritten version:|\[.*?line\]|as a journalist.*?:|title:|subtitle:', '', text)
    text = text.replace("**", "").replace("##", "").replace("`", "")
    return text.strip()

def ask_ai(title, full_content):
    """Промпт уровня Senior Editor"""
    prompt = (
        f"Act as a Senior Technology Editor for a premium digital magazine.\n"
        f"Your task: Rewrite the following source material into a compelling, expert-level article.\n\n"
        f"STRICT EDITORIAL GUIDELINES:\n"
        f"1. TONE: Professional, analytical, and engaging. Avoid tabloid cliches.\n"
        f"2. DEPTH: Minimum 5 paragraphs. Explain the 'why' and 'how', not just the 'what'.\n"
        f"3. STRUCTURE: Start with a strong lead paragraph. Use natural transitions between ideas.\n"
        f"4. UNIQUE: Use sophisticated vocabulary. Do not copy sentences from the source.\n"
        f"5. FORMAT: Line 1 must be a professional Title. Line 2 starts the article. No metadata or intros.\n\n"
        f"SOURCE TITLE: {title}\n"
        f"SOURCE CONTENT:\n{full_content[:5000]}"
    )
    try:
        result = subprocess.run(
            ["ollama", "run", "llama3", prompt],
            capture_output=True, text=True, encoding="utf-8", check=True, timeout=400
        )
        return result.stdout.strip()
    except Exception as e:
        print(f"❌ AI Error: {e}")
        return None

def run_bot():
    print(f"--- 🚀 Starting Media Engine ({len(RSS_SOURCES)} sources) ---")
    
    if not os.path.exists(DB_FILE): open(DB_FILE, 'w').close()

    for rss_url in RSS_SOURCES:
        print(f"\n📡 Checking source: {rss_url}")
        feed = feedparser.parse(rss_url)
        
        # Берем по 2 самые свежие новости с каждого источника
        for entry in feed.entries[:2]:
            with open(DB_FILE, "r") as f:
                if entry.link in f.read():
                    continue

            print(f"📄 Found: {entry.title}")
            full_content = get_full_text(entry.link)
            
            if not full_content or len(full_content) < 600:
                print("⚠️ Not enough content to rewrite, skipping...")
                continue

            print(f"🧠 AI is crafting a premium article...")
            ai_response = ask_ai(entry.title, full_content)
            
            if not ai_response or len(ai_response) < 600:
                print("⚠️ AI output too short, skipping...")
                continue

            lines = ai_response.split('\n')
            ai_title = clean_text(lines[0]).strip('"').strip("'").replace('"', "'")
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
                f.write(f"\n\n---\n*Analysis based on reporting from: {rss_url.split('/')[2]}*")

            with open(DB_FILE, "a") as f: f.write(entry.link + "\n")
            print(f"✅ Published: {ai_title}")
            
            # Небольшая пауза, чтобы не перегреть процессор
            time.sleep(2)

if __name__ == "__main__":
    run_bot()
