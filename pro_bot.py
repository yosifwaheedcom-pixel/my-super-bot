import telebot
from telebot import types, apihelper
import yt_dlp
import os
import json
import time
import hashlib
import threading
import socket
import re
import shutil
import logging
from concurrent.futures import ThreadPoolExecutor
import http.server
import socketserver

# ==========================================
# 🌐 سيرفر Flask المدمج (لإبقاء البوت حياً في Render)
# ==========================================
def start_server():
    port = int(os.environ.get("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"🌍 Server running on port {port}")
        httpd.serve_forever()

threading.Thread(target=start_server, daemon=True).start()

# ==========================================
# ⚙️ الإعدادات المتقدمة (Config)
# ==========================================
TOKEN = "8298277087:AAEv36igY-juy9TAIJHDvXwqx4k7pMF3qPM"
VERIFICATION_CODE = "4415"
QURAN_VIDEO_URL = "https://www.instagram.com/reel/DUYAQBaihUg/?igsh=Y2dhNDNuMGRiYWp3"

# تحسين أداء الشبكة
apihelper.CONNECT_TIMEOUT = 1000
apihelper.READ_TIMEOUT = 1000
apihelper.RETRY_ON_ERROR = True

BASE_DIR = "downloads"
DB_FILE = "system_db.json"
LOG_FILE = "bot_log.txt"
os.makedirs(BASE_DIR, exist_ok=True)

logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s - %(message)s')

bot = telebot.TeleBot(TOKEN, threaded=True, num_threads=40)
executor = ThreadPoolExecutor(max_workers=20)

# ==========================================
# 📊 نظام إدارة البيانات
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
# 🛡️ الحماية وعزل المستخدمين
# ==========================================
def is_owner(call, owner_id):
    if call.from_user.id != int(owner_id):
        bot.answer_callback_query(call.id, "⚠️ عذراً! هذا الطلب يخص مستخدماً آخر.", show_alert=True)
        return False
    return True

# ==========================================
# 🚀 محرك التحميل الذكي
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

            bar = self.create_progress_bar(
                d.get('downloaded_bytes', 0),
                d.get('total_bytes', 1)
            )

            text = (
                f"📥 تحميل ذكي\n"
                f"📊 {p}\n"
                f"⚡ {speed}\n"
                f"⏳ {eta}\n"
                f"{bar}"
            )
            try:
                bot.edit_message_text(text, self.chat_id, self.msg_id)
            except:
                pass

    def create_progress_bar(self, current, total):
        total = total or 1
        filled = int(10 * current / total)
        return '🟢' * filled + '⚪' * (10 - filled)

    def download(self, url, quality, file_path):
        # التعديل هنا لقراءة ملف الكوكيز المرفوع بجانب الكود
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
            'force_ipv4': True,
            'merge_output_format': 'mp4',
            'cookiefile': 'youtube.com_cookies.txt',  # تم ربط ملف الكوكيز الخاص بك هنا
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
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
            ydl_opts['format'] = f'bestvideo[height<={h}][ext=mp4]+bestaudio[ext=m4a]/best[height<={h}][ext=mp4]/best'

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            return True
        except Exception as e:
            return str(e)

# ==========================================
# 🔍 محرك البحث عبر الإنترنت
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
            'cookiefile': 'youtube.com_cookies.txt'
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
# 🤖 معالجة الأوامر والرسائل
# ==========================================
@bot.message_handler(commands=['start'])
def welcome(message):
    text = (
        "🌟 **مرحباً بك في نظام التحميل الاحترافي V2**\n\n"
        "🚀 **الميزات:** استكمال التحميل، عزل المستخدمين، توفير البيانات.\n\n"
        "📌 أرسل رابط الفيديو للبدء."
    )
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['search'])
def search_command(message):
    parts = message.text.split(maxsplit=2)
    if len(parts) < 2:
        bot.reply_to(message, "🔎 اكتب اسم الفيديو بعد الأمر")
        return

    query = parts[1]
    msg = bot.reply_to(message, "🔍 جاري البحث...")
    results = InternetSearch.search(query)

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
            types.InlineKeyboardButton("720p", callback_data=f"get_{message.from_user.id}_{message.from_user.id}_{url_hash}_720"),
            types.InlineKeyboardButton("480p", callback_data=f"get_{message.from_user.id}_{message.from_user.id}_{url_hash}_480"),
            types.InlineKeyboardButton("🎵 MP3", callback_data=f"get_{message.from_user.id}_{message.from_user.id}_{url_hash}_audio")
        )
        caption = f"🎬 {r['title']}\n📺 {r['uploader']}"
        if r.get("thumb"):
            bot.send_photo(message.chat.id, r["thumb"], caption=caption, reply_markup=markup)
        else:
            bot.send_message(message.chat.id, caption, reply_markup=markup)
    bot.delete_message(msg.chat.id, msg.message_id)

@bot.message_handler(func=lambda m: "http" in m.text)
def handle_links(message):
    user_id = message.from_user.id
    url = re.search(r'(https?://\S+)', message.text).group(1)
    
    if not Database.is_verified(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📖 شاهد المقطع", url=QURAN_VIDEO_URL))
        markup.add(types.InlineKeyboardButton("🔑 إدخال الكود", callback_data=f"verify_{user_id}"))
        bot.reply_to(message, "⛔ **وصول محدود!**\nشاهد فيديو القرآن لاستخراج الكود أولاً.", reply_markup=markup)
        return

    url_hash = hashlib.md5(url.encode()).hexdigest()[:10]
    file_id = f"{user_id}_{url_hash}"
    data = Database.load()
    data["users"][str(user_id)] = {"url": url, "file_id": file_id}
    Database.save(data)

    show_quality_options(message.chat.id, user_id, file_id)

def show_quality_options(chat_id, user_id, file_id):
    markup = types.InlineKeyboardMarkup(row_width=3)
    btns = [
        types.InlineKeyboardButton("720p", callback_data=f"get_{user_id}_{file_id}_720"),
        types.InlineKeyboardButton("480p", callback_data=f"get_{user_id}_{file_id}_480"),
        types.InlineKeyboardButton("🎵 MP3", callback_data=f"get_{user_id}_{file_id}_audio")
    ]
    markup.add(*btns)
    bot.send_message(chat_id, "🎬 **اختر الدقة:**", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    data = call.data.split('_')
    action, owner_id = data[0], data[1]
    if not is_owner(call, owner_id): return

    if action == "verify":
        msg = bot.send_message(call.message.chat.id, "🔢 **أدخل الكود المكون من 4 أرقام:**")
        bot.register_next_step_handler(msg, check_verification_code)
    elif action == "get":
        file_id, quality = data[2], data[3]
        initiate_download(call.message, owner_id, file_id, quality)

def check_verification_code(message):
    if message.text == VERIFICATION_CODE:
        Database.verify_user(message.from_user.id)
        bot.reply_to(message, "✅ تم التحقق!")
    else:
        bot.reply_to(message, "❌ الكود خاطئ!")

def initiate_download(message, user_id, file_id, quality):
    task_data = Database.load()["users"].get(str(user_id))
    if not task_data: return
    url = task_data["url"]
    ext = "mp3" if quality == "audio" else "mp4"
    file_path = f"{BASE_DIR}/{file_id}.{ext}"
    prog_msg = bot.send_message(message.chat.id, "⏳ جاري التحميل...")
    executor.submit(run_task, prog_msg, user_id, url, quality, file_path)

def run_task(prog_msg, user_id, url, quality, file_path):
    dl = SmartDownloader(prog_msg.chat.id, prog_msg.message_id, user_id)
    success = dl.download(url, quality, file_path)
    if success is True:
        try:
            bot.edit_message_text("📤 جاري الرفع الآن...", prog_msg.chat.id, prog_msg.message_id)
            with open(file_path, 'rb') as f:
                if "audio" in quality:
                    bot.send_audio(prog_msg.chat.id, f, caption="🎵 تم التحميل")
                else:
                    bot.send_video(prog_msg.chat.id, f, caption="🎬 تم التحميل")
            if os.path.exists(file_path): os.remove(file_path)
            bot.delete_message(prog_msg.chat.id, prog_msg.message_id)
        except Exception as e:
            bot.send_message(prog_msg.chat.id, f"⚠️ خطأ في الرفع: {e}")
    else:
        bot.edit_message_text(f"❌ فشل التحميل: {success}", prog_msg.chat.id, prog_msg.message_id)

if __name__ == "__main__":
    print("🚀 البوت يعمل الآن...")
    bot.infinity_polling(skip_pending=True)
                    
