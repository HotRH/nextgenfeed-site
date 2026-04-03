import feedparser
import os
import subprocess
import time
from datetime import datetime, timedelta
import re
import trafilatura
import random

# --- КОНФИГУРАЦИЯ ---
RSS_SOURCES = [
    "https://www.theverge.com/rss/index.xml",
    "https://techcrunch.com/feed/",
    "https://arstechnica.com/feed/",
    "https://www.wired.com/feed/rss",
    "https://9to5google.com/feed/"
]

# ЧЕРНЫЙ СПИСОК
STOP_WORDS = ["promo", "coupon", "deal", "discount", "off", "sale", "save", "offer", "cheap", "code", "best buys", "how to watch"]

DB_FILE = "published_urls.txt"
POSTS_DIR = "content/posts"
os.makedirs(POSTS_DIR, exist_ok=True)

def get_full_text(url):
    downloaded = trafilatura.fetch_url(url)
    if downloaded:
        return trafilatura.extract(downloaded, include_comments=False)
    return None

def clean_text(text):
    text = re.sub(r'(?i)here is the.*?article:|rewritten version:|\[.*?line\]|as a journalist.*?:', '', text)
    text = text.replace("**", "").replace("##", "").replace("`", "")
    return text.strip()

def is_trash(title):
    t = title.lower()
    return any(word in t for word in STOP_WORDS)

def ask_ai(title, full_content):
    prompt = (
        f"Act as a Senior Technology Editor. Rewrite the following news.\n"
        f"1. Professional and deep analysis (5+ paragraphs).\n"
        f"2. Catchy SEO Title on Line 1. Article starts on Line 2.\n"
        f"SOURCE TITLE: {title}\n"
        f"CONTENT: {full_content[:5000]}"
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
    print(f"--- 🚀 Starting CLEAN Media Engine ---")
    if not os.path.exists(DB_FILE): open(DB_FILE, 'w').close()

    new_articles = []
    for rss_url in RSS_SOURCES:
        feed = feedparser.parse(rss_url)
        for entry in feed.entries[:3]:
            with open(DB_FILE, "r") as f:
                if entry.link in f.read(): continue
            
            if is_trash(entry.title):
                print(f"🗑 Skipping trash: {entry.title}")
                continue
                
            new_articles.append(entry)

    if not new_articles:
        print("☕ No new clean news found.")
        return

    last_publish_time = datetime.now()

    for entry in new_articles:
        random_delay = random.randint(40, 60)
        last_publish_time += timedelta(minutes=random_delay)
        
        print(f"📄 Processing: {entry.title}")
        full_content = get_full_text(entry.link)
        if not full_content or len(full_content) < 600: continue

        ai_response = ask_ai(entry.title, full_content)
        if not ai_response or len(ai_response) < 600: continue

        lines = ai_response.split('\n')
        ai_title = clean_text(lines[0]).strip('"').strip("'").replace('"', "'")
        article_body = clean_text("\n".join(lines[1:]))

        timestamp = int(last_publish_time.timestamp())
        post_filename = os.path.join(POSTS_DIR, f"post_{timestamp}.md")

        with open(post_filename, "w", encoding="utf-8") as f:
            f.write('---\n')
            f.write(f'title: "{ai_title}"\n')
            f.write(f'date: {last_publish_time.strftime("%Y-%m-%dT%H:%M:%SZ")}\n')
            f.write('draft: false\n')
            f.write('---\n\n')
            f.write(article_body)
            f.write(f"\n\n---\n*Analysis based on: {entry.link}*")

        with open(DB_FILE, "a") as f: f.write(entry.link + "\n")
        print(f"✅ Success: {ai_title}")

if __name__ == "__main__":
    run_bot()
