from sent_articles import init_db, save_article, is_article_saved, get_all_articles
import os
import feedparser
import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder
from datetime import datetime, timedelta, time
import requests
from bs4 import BeautifulSoup

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")

init_db()

RSS_FEEDS = [
    'https://www.nintenderos.com/feed',
    'https://www.nintendo.com/es/news/rss.xml',
    'https://nintenduo.com/category/noticias/feed/',
    'https://www.xataka.com/tag/nintendo/rss',
]

async def send_news(context, entry):
    # Filtrar noticias recientes (últimas 3 horas)
    if hasattr(entry, 'published_parsed'):
        published = datetime(*entry.published_parsed[:6])
        if datetime.now() - published > timedelta(hours=3):
            return

    # Filtrar SOLO noticias relacionadas con Nintendo
    title_lower = entry.title.lower()
    summary_lower = (entry.summary if hasattr(entry, 'summary') else "").lower()

    if not any(palabra in title_lower or palabra in summary_lower for palabra in [
        "nintendo", "switch", "zelda", "mario", "pokemon", "metroid", "kirby", "joy-con", "nintendogs", "smash bros"
    ]):
        return

    link = entry.link
    photo_url = None

    if entry.get("media_content"):
        for m in entry.media_content:
            if m.get("type", "").startswith("image/"):
                photo_url = m.get("url")
                break
    if not photo_url and entry.get("enclosures"):
        for enc in entry.enclosures:
            if enc.get("type", "").startswith("image/"):
                photo_url = enc.get("url")
                break
    if not photo_url:
        try:
            r = requests.get(entry.link, timeout=5)
            soup = BeautifulSoup(r.text, 'html.parser')
            og_image = soup.find('meta', property='og:image')
            if og_image and og_image.get('content'):
                photo_url = og_image.get('content')
        except Exception as e:
            print(f"Error obteniendo imagen por scraping: {e}")

    caption = f"🍄 *NINTENDO NEWS*\n\n*{entry.title}*\n\n#Nintendo"
    button = InlineKeyboardMarkup([[InlineKeyboardButton("📰 Leer noticia completa", url=entry.link)]])

    try:
        if photo_url:
            await context.bot.send_photo(
                chat_id=CHANNEL_USERNAME,
                photo=photo_url,
                caption=caption,
                parse_mode=telegram.constants.ParseMode.MARKDOWN,
                reply_markup=button
            )
        else:
            await context.bot.send_message(
                chat_id=CHANNEL_USERNAME,
                text=caption,
                parse_mode=telegram.constants.ParseMode.MARKDOWN,
                disable_web_page_preview=False,
                reply_markup=button
            )
        if hasattr(entry, 'published_parsed'):
            published = datetime(*entry.published_parsed[:6])
        else:
            published = datetime.now()
        save_article(entry.link, published)
    except Exception as e:
        print(f"Error al enviar noticia: {e}")

async def check_feeds(context):
    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            if is_article_saved(entry.link):
                continue
            await send_news(context, entry)

def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    job_queue = application.job_queue
    job_queue.run_repeating(check_feeds, interval=600, first=10)
    print("Bot Nintendo iniciado correctamente.")
    application.run_polling()

if __name__ == "__main__":
    main()
