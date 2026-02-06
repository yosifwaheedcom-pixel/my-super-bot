# ==========================================
# 📦 IMPORTS
# ==========================================
import telebot
from telebot import types, apihelper
import yt_dlp
import os
import json
import time
import hashlib
import threading
import logging
from concurrent.futures import ThreadPoolExecutor
import re
from flask import Flask
from threading import Thread

# ==========================================
# 🌐 KEEP ALIVE SERVER (Flask)
# ==========================================
app = Flask('')

@app.route('/')
def home():
    return "<b>Telegram Bot is Running by Your Name! 🚀</b>"

def run():
    # Render يعطيك PORT تلقائي
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

keep_alive()

# ==========================================
# 🍪 COOKIES SETUP
# ==========================================
COOKIES_FILE = "youtube.com_cookies.txt"

if not os.path.exists(COOKIES_FILE):
    print("⚠️ لم يتم العثور على ملف الكوكيز، تأكد من وجود youtube.com_cookies.txt")
else:
    print("✅ ملف الكوكيز جاهز!")

# ==========================================
# ⚙️ CONFIG
# ==========================================
TOKEN = "8298277087:AAEv36igY-juy9TAIJHDvXwqx4k7pMF3qPM"
VERIFICATION_CODE = "4415"
QURAN_VIDEO_URL = "https://www.instagram.com/reel/DUYAQBaihUg/?igsh=Y2dhNDNuMGRiYWp3"

apihelper.CONNECT_TIMEOUT = 1000
apihelper.READ_TIMEOUT = 1000
apihelper.RETRY_ON_ERROR = True

BASE_DIR = "downloads"
DB_FILE = "system_db.json"
LOG_FILE = "bot_log.txt"

os.makedirs(BASE_DIR, exist_ok=True)
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s - %(message)s')

# ==========================================
# 🐝 BOT INIT
# ==========================================
bot = telebot.TeleBot(TOKEN, threaded=True, num_threads=40)
executor = ThreadPoolExecutor(max_workers=20)

# ==========================================
# 📊 DATABASE SYSTEM
# ==========================================
class Database:
    @staticmethod
    def load():
        if not os.path.exists(DB_FILE):
            return {"users": {}, "verified": [], "stats": {"total_dl": 0}}
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except:
            return {"users": {}, "verified": [], "stats": {"total_dl": 0}}

    @staticmethod
    def save(data):
        with open(DB_FILE, "w") as f:
            json.dump(data, f, indent=4)

    @staticmethod
    def is_verified(user_id):
        return str(user_id) in Database.load().get("verified", [])

    @staticmethod
    def verify_user(user_id):
        data = Database.load()
        if str(user_id) not in data["verified"]:
            data["verified"].append(str(user_id))
            Database.save(data)

# ==========================================
# 🛡️ SECURITY
# ==========================================
def is_owner(call, owner_id):
    if call.from_user.id != int(owner_id):
        bot.answer_callback_query(call.id, "⚠️ هذا الطلب يخص مستخدم آخر.", show_alert=True)
        return False
    return True

# ==========================================
# 🚀 SMART DOWNLOADER
# ==========================================
class SmartDownloader:
    def __init__(self, chat_id, message_id, user_id):
        self.chat_id = chat_id
        self.msg_id = message_id
        self.user_id = user_id
        self.last_update_time = 0

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            now = time.time()
            if now - self.last_update_time < 5:
                return
            self.last_update_time = now

            p = d.get('_percent_str', '0%')
            speed = d.get('_speed_str', 'N/A')
            eta = d.get('_eta_str', 'N/A')
            bar = self.create_progress_bar(d.get('downloaded_bytes',0), d.get('total_bytes',1))

            text = f"📥 تحميل ذكي\n📊 {p}\n⚡ {speed}\n⏳ {eta}\n{bar}"
            try:
                bot.edit_message_text(text, self.chat_id, self.msg_id)
            except: pass

    def create_progress_bar(self, current, total):
        total = total or 1
        filled = int(10 * current / total)
        return '🟢' * filled + '⚪' * (10 - filled)

    def download(self, url, quality, file_path):
        ydl_opts = {
            'outtmpl': file_path,
            'continuedl': True,
            'retries': 50,
            'fragment_retries': 50,
            'socket_timeout': 30,
            'progress_hooks': [self.progress_hook],
            'quiet': True,
            'no_warnings': True,
            'geo_bypass': True,
            'merge_output_format': 'mp4',
            'cookiefile': COOKIES_FILE,
            'http_headers': {
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/120.0.0.0 Safari/537.36'
                )
            }
        }

        if quality == 'audio':
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192'
            }]
        else:
            try:
                h = int(quality)
            except:
                h = 720
            ydl_opts['format'] = f'bestvideo[height<={h}]+bestaudio/best'

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            return True
        except Exception as e:
            return str(e)

# ==========================================
# 🔍 INTERNET SEARCH
# ==========================================
class InternetSearch:
    @staticmethod
    def search(query, limit=5):
        results = []
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'force_ipv4': True,
            'cookiefile': COOKIES_FILE
        }
        search_query = f"ytsearch{limit}:{query}"
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(search_query, download=False)
                for e in info.get('entries', []):
                    results.append({
                        "title": e.get("title", "بدون عنوان"),
                        "url": e.get("url"),
                        "thumb": e.get("thumbnail"),
                        "duration": e.get("duration", 0),
                        "uploader": e.get("uploader", "غير معروف")
                    })
            except:
                pass
        return results

# ==========================================
# 🤖 MESSAGE HANDLERS
# ==========================================
@bot.message_handler(commands=['start'])
def welcome(message):
    text = (
        "🌟 مرحباً بك في نظام التحميل الاحترافي V2\n"
        "🚀 الميزات: استكمال التحميل، عزل المستخدمين، توفير البيانات.\n"
        "📌 أرسل رابط الفيديو (Youtube, TikTok, Facebook, Instagram) للبدء."
    )
    bot.send_message(message.chat.id, text)

# ==========================================
# SEARCH COMMAND
# ==========================================
@bot.message_handler(commands=['search'])
def search_command(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "🔎 اكتب اسم الفيديو بعد الأمر\nمثال:\n/search توم وجيري")
        return
    query = parts[1]
    msg = bot.reply_to(message, "🔍 جاري البحث من الإنترنت...")
    results = InternetSearch.search(query, limit=5)
    if not results:
        bot.edit_message_text("❌ لم يتم العثور على نتائج.", msg.chat.id, msg.message_id)
        return
    for r in results:
        url_hash = hashlib.md5(r["url"].encode()).hexdigest()[:10]
        data = Database.load()
        data["users"][str(message.from_user.id)] = {"url": r["url"], "file_id": f"{message.from_user.id}_{url_hash}"}
        Database.save(data)
        markup = types.InlineKeyboardMarkup(row_width=4)
        markup.add(
            types.InlineKeyboardButton("1080p", callback_data=f"get_{message.from_user.id}_{url_hash}_1080"),
            types.InlineKeyboardButton("720p", callback_data=f"get_{message.from_user.id}_{url_hash}_720"),
            types.InlineKeyboardButton("480p", callback_data=f"get_{message.from_user.id}_{url_hash}_480"),
            types.InlineKeyboardButton("🎵 MP3", callback_data=f"get_{message.from_user.id}_{url_hash}_audio")
        )
        caption = f"🎬 {r['title']}\n⏱ {r['duration']} ثانية\n📺 {r['uploader']}"
        if r.get("thumb"):
            bot.send_photo(message.chat.id, r["thumb"], caption=caption, reply_markup=markup)
        else:
            bot.send_message(message.chat.id, caption, reply_markup=markup)
    bot.delete_message(msg.chat.id, msg.message_id)

# ==========================================
# HANDLE URL MESSAGES
# ==========================================
@bot.message_handler(func=lambda m: "http" in m.text)
def handle_links(message):
    user_id = message.from_user.id
    url = re.search(r'(https?://\S+)', message.text).group(1)
    if not Database.is_verified(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📖 شاهد المقطع", url=QURAN_VIDEO_URL))
        markup.add(types.InlineKeyboardButton("🔑 إدخال الكود", callback_data=f"verify_{user_id}"))
        bot.reply_to(message, "⛔ وصول محدود! شاهد الفيديو لاستخراج الكود.", reply_markup=markup)
        return
    url_hash = hashlib.md5(url.encode()).hexdigest()[:10]
    file_id = f"{user_id}_{url_hash}"
    data = Database.load()
    data["users"][str(user_id)] = {"url": url, "file_id": file_id}
    Database.save(data)
    partial_path = f"{BASE_DIR}/{file_id}.mp4.part"
    if os.path.exists(partial_path):
        size = os.path.getsize(partial_path) / (1024*1024)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(f"✅ إكمال التحميل ({size:.1f}MB)", callback_data=f"resume_{user_id}_{file_id}"))
        markup.add(types.InlineKeyboardButton("❌ حذف والبدء من جديد", callback_data=f"restart_{user_id}_{file_id}"))
        bot.reply_to(message, "🔍 تم العثور على جزء من الفيديو، اختر:", reply_markup=markup)
    else:
        show_quality_options(message.chat.id, user_id, file_id)

def show_quality_options(chat_id, user_id, file_id):
    markup = types.InlineKeyboardMarkup(row_width=3)
    btns = [
        types.InlineKeyboardButton("1080p", callback_data=f"get_{user_id}_{file_id}_1080"),
        types.InlineKeyboardButton("720p", callback_data=f"get_{user_id}_{file_id}_720"),
        types.InlineKeyboardButton("480p", callback_data=f"get_{user_id}_{file_id}_480"),
        types.InlineKeyboardButton("360p", callback_data=f"get_{user_id}_{file_id}_360"),
        types.InlineKeyboardButton("144p", callback_data=f"get_{user_id}_{file_id}_144"),
        types.InlineKeyboardButton("🎵 MP3", callback_data=f"get_{user_id}_{file_id}_audio")
    ]
    markup.add(*btns)
    bot.send_message(chat_id, "🎬 اختر الدقة:", reply_markup=markup)

# ==========================================
# CALLBACK HANDLER
# ==========================================
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    data = call.data.split('_')
    action = data[0]
    owner_id = data[1]
    if not is_owner(call, owner_id): return
    if action == "verify":
        msg = bot.send_message(call.message.chat.id, "🔢 أدخل الكود المكون من 4 أرقام:")
        bot.register_next_step_handler(msg, check_verification_code)
    elif action == "get":
        file_id, quality = data[2], data[3]
        initiate_download(call.message, owner_id, file_id, quality)
    elif action == "resume":
        file_id = data[2]
        initiate_download(call.message, owner_id, file_id, "720")
    elif action == "restart":
        file_id = data[2]
        for f in os.listdir(BASE_DIR):
            if file_id in f: os.remove(os.path.join(BASE_DIR, f))
        show_quality_options(call.message.chat.id, owner_id, file_id)

# ==========================================
# VERIFICATION & DOWNLOAD LOGIC
# ==========================================
def check_verification_code(message):
    if message.text == VERIFICATION_CODE:
        Database.verify_user(message.from_user.id)
        bot.reply_to(message, "✅ تم التحقق! يمكنك الآن استخدام البوت.")
    else:
        bot.reply_to(message, "❌ الكود خاطئ!")

def initiate_download(message, user_id, file_id, quality):
    task_data = Database.load()["users"].get(str(user_id))
    if not task_data: return
    url = task_data["url"]
    ext = "mp3" if quality == "audio" else "mp4"
    file_path = f"{BASE_DIR}/{file_id}.{ext}"
    prog_msg = bot.send_message(message.chat.id, "⏳ جاري التحضير...")
    executor.submit(run_task, prog_msg, user_id, url, quality, file_path)

def run_task(prog_msg, user_id, url, quality, file_path):
    dl = SmartDownloader(prog_msg.chat.id, prog_msg.message_id, user_id)
    success = dl.download(url, quality, file_path)
    if success is True:
        try:
            bot.edit_message_text("📤 تم التحميل! جاري الإرسال...", prog_msg.chat.id, prog_msg.message_id)
            with open(file_path, 'rb') as f:
                if "audio" in quality:
                    bot.send_audio(prog_msg.chat.id, f, caption="🎵 تم التحميل بنجاح")
                else:
                    bot.send_video(prog_msg.chat.id, f, caption="🎬 تم التحميل بنجاح")
            if os.path.exists(file_path): os.remove(file_path)
            bot.delete_message(prog_msg.chat.id, prog_msg.message_id)
        except Exception as e:
            logging.error(e)
    else:
        bot.edit_message_text(f"❌ خطأ أثناء التحميل: {success}", prog_msg.chat.id, prog_msg.message_id)

# ==========================================
# 🔔 START BOT
# ==========================================
if __name__ == "__main__":
    print("🤖 البوت شغال الآن!")
    bot.infinity_polling(skip_pending=True)
