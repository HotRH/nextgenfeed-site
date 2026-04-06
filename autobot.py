import feedparser
import os
import subprocess
import time
from datetime import datetime, timedelta
import re
import trafilatura
import random
import requests
import urllib.parse

# --- КОНФИГУРАЦИЯ ---
PIXABAY_KEY = "12478360-27bd55f31c4bdf8f739410ef4" # <--- Твой ключ от Pixabay

RSS_SOURCES = [
    "https://www.theverge.com/rss/index.xml",
    "https://techcrunch.com/feed/",
    "https://arstechnica.com/feed/",
    "https://www.wired.com/feed/rss",
    "https://9to5google.com/feed/"
]

STOP_WORDS = [
    "promo", "coupon", "deal", "discount", "off", "sale", "save", 
    "offer", "cheap", "code", "best buys", "how to watch",
    "all-time low", "price drop", "lowest price", "buying guide", 
    "gift guide", "$"
]

DB_FILE = "published_urls.txt"
TITLES_FILE = "published_titles.txt"
POSTS_DIR = "content/posts"
os.makedirs(POSTS_DIR, exist_ok=True)

def get_full_text(url):
    downloaded = trafilatura.fetch_url(url)
    return trafilatura.extract(downloaded, include_comments=False) if downloaded else None

def clean_text(text):
    text = re.sub(r'(?i)here is the.*?article:|rewritten version:|\[.*?line\]|as a journalist.*?:', '', text)
    text = re.sub(r'(?i)follow.*?(twitter|x|threads|bluesky|instagram|facebook).*', '', text)
    return text.replace("**", "").replace("##", "").replace("`", "").strip()

def is_trash(title):
    t = title.lower()
    return any(word in t for word in STOP_WORDS)

def is_semantic_duplicate(new_title):
    if not os.path.exists(TITLES_FILE): return False
    with open(TITLES_FILE, "r", encoding="utf-8") as f:
        past_titles = f.readlines()[-15:]
    if not past_titles: return False

    titles_str = "".join(past_titles)
    prompt = (
        f"You are a strict news editor. Check if the NEW TITLE is about the EXACT same specific news event as ANY of the PAST TITLES.\n"
        f"Answer strictly with one word: YES (if it is the same event) or NO (if it is a different event).\n\n"
        f"PAST TITLES:\n{titles_str}\n"
        f"NEW TITLE: {new_title}"
    )
    try:
        result = subprocess.run(["ollama", "run", "llama3", prompt], capture_output=True, text=True, encoding="utf-8", timeout=60)
        return True if "YES" in result.stdout.strip().upper() else False
    except: return False

def get_image_keyword(title):
    """ИИ придумывает идеальный запрос для фотостока"""
    prompt = f"Give me exactly TWO English keywords to find a stock photo for this tech news. DO NOT write sentences. JUST TWO WORDS.\nNews Title: {title}"
    try:
        result = subprocess.run(["ollama", "run", "llama3", prompt], capture_output=True, text=True, encoding="utf-8", timeout=60)
        words = result.stdout.strip().replace('"', '').replace("Keywords:", "").strip()
        return words
    except:
        return "technology"

def get_pixabay_image(query):
    """Ищет легальную картинку на Pixabay"""
    if PIXABAY_KEY == "12478360-27bd55f31c4bdf8f739410ef4": return ""
    
    clean_query = urllib.parse.quote(query)
    url = f"https://pixabay.com/api/?key={PIXABAY_KEY}&q={clean_query}&image_type=photo&orientation=horizontal&category=science&safesearch=true&per_page=3"
    
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        if data.get('totalHits', 0) > 0:
            return data['hits'][0]['largeImageURL']
    except:
        pass
    return ""

def ask_ai(title, full_content):
    prompt = (
        f"Act as a Senior Technology Editor. Rewrite this news into a deep analysis (5+ paragraphs).\n"
        f"IMPORTANT: DO NOT include any author names, bios, or 'Follow me' social media links.\n"
        f"Line 1: Catchy SEO Title. Line 2: Start article.\n"
        f"SOURCE: {title}\nCONTENT: {full_content[:5000]}"
    )
    try:
        result = subprocess.run(["ollama", "run", "llama3", prompt], capture_output=True, text=True, encoding="utf-8", timeout=400)
        return result.stdout.strip()
    except: return None

def run_bot():
    print(f"--- 🚀 Smart Scheduler & AI Deduplicator Active ---")
    if not os.path.exists(DB_FILE): open(DB_FILE, 'w').close()
    if not os.path.exists(TITLES_FILE): open(TITLES_FILE, 'w').close()

    collected = []
    for rss_url in RSS_SOURCES:
        feed = feedparser.parse(rss_url)
        for entry in feed.entries[:4]:
            with open(DB_FILE, "r") as f:
                if entry.link in f.read(): continue
            
            if is_trash(entry.title) or "/deals/" in entry.link or "/good-deals/" in entry.link:
                continue
            
            if is_semantic_duplicate(entry.title):
                continue

            collected.append(entry)
    
    if not collected:
        print("☕ No new unique articles.")
        return

    to_process = collected[:5]
    last_time = datetime.now()

    for entry in to_process:
        gap = random.randint(45, 60)
        last_time += timedelta(minutes=gap)
        
        full_content = get_full_text(entry.link)
        if not full_content or len(full_content) < 500: continue

        ai_res = ask_ai(entry.title, full_content)
        if not ai_res or len(ai_res) < 500: continue

        lines = ai_res.split('\n')
        ai_title = clean_text(lines[0]).strip('"').replace('"', "'")
        body = clean_text("\n".join(lines[1:]))

        if "generation error" in body.lower() or "generation error" in ai_title.lower():
            print(f"⚠️ Error detected, skipping: {entry.title}")
            continue

        seo_desc = re.sub(r'[\n\r\"\'*#]', ' ', body[:160]).strip() + "..."
        
        # МАГИЯ КАРТИНОК: ИИ думает -> Pixabay ищет
        search_query = get_image_keyword(ai_title)
        print(f"🔍 AI suggests image keywords: {search_query}")
        image_url = get_pixabay_image(search_query)

        filename = os.path.join(POSTS_DIR, f"post_{int(last_time.timestamp())}.md")
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f'---\n')
            f.write(f'title: "{ai_title}"\n')
            f.write(f'date: {last_time.strftime("%Y-%m-%dT%H:%M:%SZ")}\n')
            f.write(f'lastmod: {last_time.strftime("%Y-%m-%dT%H:%M:%SZ")}\n')
            f.write(f'description: "{seo_desc}"\n')
            if image_url:
                f.write(f'thumbnail: "{image_url}"\n')
            f.write(f'draft: false\n')
            f.write(f'---\n\n')
            f.write(body + f"\n\n---\n*Source: {entry.link}*")

        with open(DB_FILE, "a") as f: f.write(entry.link + "\n")
        with open(TITLES_FILE, "a", encoding="utf-8") as f: f.write(entry.title + "\n")
        
        print(f"✅ Scheduled: {ai_title} (🖼️ Image: {'Yes' if image_url else 'No'})")

if __name__ == "__main__":
    run_bot()
