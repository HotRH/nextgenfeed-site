import feedparser
import os
import subprocess

# --- КОНФИГУРАЦИЯ ---
RSS_URL = "https://www.theverge.com/rss/index.xml" # Качественные техно-новости (ENG)
DB_FILE = "published_urls.txt"
POSTS_DIR = "content/posts"

# Создаем папку, если ее нет
os.makedirs(POSTS_DIR, exist_ok=True)

def is_published(url):
    """Проверка: была ли эта новость уже опубликована"""
    if not os.path.exists(DB_FILE):
        return False
    with open(DB_FILE, "r") as f:
        return url in f.read()

def mark_as_published(url):
    """Записываем ссылку в базу, чтобы не дублировать"""
    with open(DB_FILE, "a") as f:
        f.write(url + "\n")

def ask_ai(title, summary):
    """Запрос к Ollama (Llama 3) для рерайта"""
    prompt = (
        f"Act as a tech journalist. Rewrite the following news in professional English for a global audience. "
        f"The output must start with a new catchy title on the first line, then one blank line, then the article body. "
        f"Do not include any intro like 'Here is the rewrite'. Start directly with the title.\n\n"
        f"Original Title: {title}\nOriginal Content: {summary}"
    )
    
    try:
        # Запускаем локальную нейросеть
        result = subprocess.run(
            ["ollama", "run", "llama3", prompt],
            capture_output=True, text=True, encoding="utf-8", check=True
        )
        return result.stdout.strip()
    except Exception as e:
        print(f"Error calling Ollama: {e}")
        return None

def run_bot():
    print("--- Starting AutoBot ---")
    feed = feedparser.parse(RSS_URL)
    
    # Берем последние 5 новостей из ленты
    for entry in feed.entries[:5]:
        if is_published(entry.link):
            print(f"Skipping: {entry.title} (already published)")
            continue

        print(f"Processing: {entry.title}...")
        ai_response = ask_ai(entry.title, entry.summary)

        if not ai_response or len(ai_response) < 50:
            print("Skipping due to AI error.")
            continue

        # Парсим ответ: 1-я строка заголовок, остальное текст
        lines = ai_response.split('\n', 1)
        ai_title = lines[0].strip().replace('"', "'")
        article_body = lines[1].strip() if len(lines) > 1 else ai_response

        # Генерируем уникальное имя файла
        file_id = "".join(x for x in ai_title[:20] if x.isalnum() or x==' ').replace(' ', '_').lower()
        filename = os.path.join(POSTS_DIR, f"{file_id}.md")

        # Картинка: берем первое слово заголовка как тег для Unsplash
        keyword = ai_title.split()[0].lower()
        image_url = f"https://source.unsplash.com/800x600/?tech,{keyword}"

        # Записываем файл для Hugo
        with open(filename, "w", encoding="utf-8") as f:
            f.write('---\n')
            f.write(f'title: "{ai_title}"\n')
            f.write(f'date: {entry.get("published", "2026-03-28")}\n')
            f.write(f'thumbnail: "{image_url}"\n')
            f.write('draft: false\n')
            f.write('---\n\n')
            f.write(article_body)

        mark_as_published(entry.link)
        print(f"Done: {ai_title}")

if __name__ == "__main__":
    run_bot()
    print("--- Finished! ---")
