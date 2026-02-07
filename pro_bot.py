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
import os
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "<b>Status: Online 🚀</b>"

def run():
    # Render يمرر البورت عبر متغير بيئة يسمى PORT
    port = int(os.environ.get("PORT", 8080)) 
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# تشغيل السيرفر قبل أي شيء آخر
keep_alive()
#==========================================

#🍪 منطقة الكوكيز (تم التصحيح لتعمل مع بايثون)

#==========================================
#==========================================

#⚙️ الإعدادات المتقدمة (Config)

#==========================================

TOKEN = "8298277087:AAEv36igY-juy9TAIJHDvXwqx4k7pMF3qPM"
VERIFICATION_CODE = "4415"
QURAN_VIDEO_URL = "https://www.instagram.com/reel/DUYAQBaihUg/?igsh=Y2dhNDNuMGRiYWp3"

#تحسين أداء الشبكة للنت الضعيف جداً

apihelper.CONNECT_TIMEOUT = 1000
apihelper.READ_TIMEOUT = 1000
apihelper.RETRY_ON_ERROR = True

#المجلدات وقواعد البيانات

BASE_DIR = "downloads"
DB_FILE = "system_db.json"
LOG_FILE = "bot_log.txt"
os.makedirs(BASE_DIR, exist_ok=True)

#نظام تسجيل الأخطاء

logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s - %(message)s')

#تهيئة البوت مع نظام خيوط المعالجة

bot = telebot.TeleBot(TOKEN, threaded=True, num_threads=40)
executor = ThreadPoolExecutor(max_workers=20)
# تهيئة قاعدة البيانات عند أول تشغيل
if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w") as f:
        json.dump({"users": {}, "verified": [], "stats": {"total_dl": 0}}, f)
    print("📋 تم إنشاء قاعدة البيانات الجديدة بنجاح!")
    
#==========================================

#📊 نظام إدارة البيانات

#==========================================

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
            

#==========================================

#🛡️ الحماية وعزل المستخدمين

#=========================================
def is_owner(call, owner_id):
    if call.from_user.id != int(owner_id):
        bot.answer_callback_query(call.id, "⚠️ عذراً! هذا الطلب يخص مستخدماً آخر. أرسل رابطك الخاص.", show_alert=True)
        return False
    return True

#==========================================

#🚀 محرك التحميل الذكي

#==========================================
#==========================================
# 🚀 محرك التحميل الذكي (SmartDownloader)
#==========================================

class SmartDownloader:
    def __init__(self, chat_id, message_id, user_id):
        self.chat_id = chat_id
        self.msg_id = message_id
        self.user_id = user_id
        self.last_update_time = 0

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            now = time.time()
            # تحديث الرسالة كل 5 ثوانٍ فقط لتجنب حظر التلجرام (Flood)
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
                f"📥 <b>جاري التحميل الذكي...</b>\n\n"    
                f"📊 المكتمل: {p}\n"    
                f"⚡ السرعة: {speed}\n"    
                f"⏳ الوقت المتبقي: {eta}\n"    
                f"<code>{bar}</code>"    
            )    
            try:    
                bot.edit_message_text(text, self.chat_id, self.msg_id, parse_mode="HTML")    
            except:    
                pass

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
            'geo_bypass_country': 'US',
            'force_ipv4': True,
            'merge_output_format': 'mp4',
            'cookiefile': 'cookies.txt',
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web', 'tv_embedded'],
                    'skip': ['hls', 'dash'],
                    'player_skip': ['configs'],
                }
            },
            'http_headers': {
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/120.0.0.0 Safari/537.36'
                )
            }
        }

        # تحديد الجودة المطلوبة
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
            ydl_opts['format'] = (    
                f'bestvideo[height<={h}][ext=mp4]+bestaudio[ext=m4a]/'    
                f'best[height<={h}][ext=mp4]/best'    
            )    

        try:    
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:    
                ydl.download([url])    
            return True    
        except Exception as e:    
            return str(e)
            

#==========================================

#🔍  البحث عبر الإنترنت محرك

#==========================================
#==========================================
# 🔍 محرك البحث عبر الإنترنت (InternetSearch)
#==========================================
class InternetSearch:
    @staticmethod
    def search(query, platform='tiktok', limit=5):
        results = []
        # تحديد الموقع بناءً على الاختصار
        platform_map = {
            'tik': 'tiktok',
            'ins': 'instagram',
            'fb': 'facebook',
            'tw': 'twitter'
        }
        target = platform_map.get(platform, 'tiktok')
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'force_ipv4': True,
            'ignoreerrors': True,
        }
        
        # البحث في المنصة المحددة
        search_query = f"{target}search{limit}:{query}"
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(search_query, download=False)
                for e in info.get('entries', []):
                    if e:
                        results.append({
                            "title": e.get("title", "فيديو بدون عنوان"),
                            "url": e.get("url"),
                            "uploader": e.get("uploader", target.capitalize())
                        })
            except: pass
        return results
        
                        

#========================================# ==========================================
# 🤖 معالجة الأوامر والرسائل
# ==========================================

@bot.message_handler(commands=['start'])
def welcome(message):
    help_text = (
        "🚀 **أهلاً بك في نظام التحميل الشامل V2**\n"
        "تم تحسين النظام ليتجاوز قيود يوتيوب والتركيز على المنصات العالمية.\n\n"
        "📌 **كيفية التحميل:**\n"
        "فقط أرسل رابط الفيديو من (TikTok, Instagram, FB) وسأقوم بالباقي.\n\n"
        "🔍 **كيفية البحث الذكي:**\n"
        "• للتيك توك: `/search tik [كلمة البحث]`\n"
        "• للإنستجرام: `/search ins [كلمة البحث]`\n"
        "• للفيسبوك: `/search fb [كلمة البحث]`\n\n"
        "⚡ **ميزات النظام:**\n"
        "- استكمال التحميل تلقائياً.\n"
        "- فحص الجودة قبل البدء.\n"
        "- حماية الخصوصية ونظام إدارة المهام المتطور."
    )
    bot.send_message(message.chat.id, help_text, parse_mode="Markdown")

@bot.message_handler(commands=['status'])
def server_status(message):
    try:
        import psutil
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        status = (
            "🖥 **حالة النظام المتطور:**\n\n"
            f"⚙️ استهلاك المعالج: {cpu}%\n"
            f"🧠 استهلاك الذاكرة: {ram}%\n"
            "📡 الحالة: متصل ومحمي بنظام التشفير."
        )
        bot.reply_to(message, status, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, "⚠️ ميزة مراقبة النظام تحتاج لتثبيت مكتبة psutil.")

@bot.message_handler(commands=['search'])
def search_command(message):
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        bot.reply_to(message, "⚠️ طريقة البحث الصحيحة:\n/search tik توم وجيري\n/search ins مضحك")
        return

    platform = parts[1].lower()
    query = parts[2]
    
    msg = bot.reply_to(message, f"🔍 جاري البحث في {platform}...")
    results = InternetSearch.search(query, platform=platform)
    
    if not results:
        bot.edit_message_text("❌ لم يتم العثور على نتائج لهذه المنصة.", msg.chat.id, msg.message_id)
        return

    for r in results:
        url_hash = hashlib.md5(r["url"].encode()).hexdigest()[:10]
        user_id = message.from_user.id
        
        # تخزين بيانات البحث مؤقتاً
        data = Database.load()
        data["users"][str(user_id)] = {
            "url": r["url"],
            "file_id": f"{user_id}_{url_hash}"
        }
        Database.save(data)

        markup = types.InlineKeyboardMarkup(row_width=3)    
        markup.add(    
            types.InlineKeyboardButton("720p", callback_data=f"get_{user_id}_{user_id}_{url_hash}_720"),    
            types.InlineKeyboardButton("480p", callback_data=f"get_{user_id}_{user_id}_{url_hash}_480"),    
            types.InlineKeyboardButton("🎵 MP3", callback_data=f"get_{user_id}_{user_id}_{url_hash}_audio")    
        )    

        caption = f"🎬 {r['title']}\n📺 المنصة: {r['uploader']}"
        bot.send_message(message.chat.id, caption, reply_markup=markup)

    bot.delete_message(msg.chat.id, msg.message_id)
        
                         

#==========================================
# 🔎 أمر البحث عن الفيديوهات
#==========================================
@bot.message_handler(commands=['search'])
def search_command(message):
    parts = message.text.split(maxsplit=2)
    # /search [platform] [query]
    if len(parts) < 3:
        bot.reply_to(message, "⚠️ طريقة البحث الصحيحة:\n/search tik توم وجيري\n/search ins مضحك")
        return

    platform = parts[1].lower()
    query = parts[2]
    
    msg = bot.reply_to(message, f"🔍 جاري البحث في {platform}...")
    results = InternetSearch.search(query, platform=platform)
    
    if not results:
        bot.edit_message_text("❌ لم يتم العثور على نتائج لهذه المنصة.", msg.chat.id, msg.message_id)
        return

    for r in results:
        # هنا نستخدم نفس منطق الأزرار السابق
        # ... (بقية الكود الخاص بإرسال النتائج والأزرار)
        :
        url_hash = hashlib.md5(r["url"].encode()).hexdigest()[:10]
        data = Database.load()
        data["users"][str(message.from_user.id)] = {
            "url": r["url"],
            "file_id": f"{message.from_user.id}_{url_hash}"
        }
        Database.save(data)

        # أزرار التحميل المباشر    
        markup = types.InlineKeyboardMarkup(row_width=4)    
        markup.add(    
            types.InlineKeyboardButton("1080p", callback_data=f"get_{message.from_user.id}_{message.from_user.id}_{url_hash}_1080"),    
            types.InlineKeyboardButton("720p", callback_data=f"get_{message.from_user.id}_{message.from_user.id}_{url_hash}_720"),    
            types.InlineKeyboardButton("480p", callback_data=f"get_{message.from_user.id}_{message.from_user.id}_{url_hash}_480"),    
            types.InlineKeyboardButton("🎵 MP3", callback_data=f"get_{message.from_user.id}_{message.from_user.id}_{url_hash}_audio")    
        )    

        # إرسال صورة الفيديو مع المعلومات    
        caption = f"🎬 {r['title']}\n⏱ {r['duration']} ثانية\n📺 {r['uploader']}"    
        if r.get("thumb"):    
            bot.send_photo(message.chat.id, r["thumb"], caption=caption, reply_markup=markup)    
        else:    
            bot.send_message(message.chat.id, caption, reply_markup=markup)

    bot.delete_message(msg.chat.id, msg.message_id)

@bot.message_handler(func=lambda m: "http" in m.text)
def handle_links(message):
    user_id = message.from_user.id
    url_match = re.search(r'(https?://\S+)', message.text)
    
    if not url_match:
        return
    
    url = url_match.group(1)

    # التحقق من الأمان
    if not Database.is_verified(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📖 شاهد المقطع (استخراج الكود)", url=QURAN_VIDEO_URL))
        markup.add(types.InlineKeyboardButton("🔑 إدخال الكود", callback_data=f"verify_{user_id}"))
        bot.reply_to(message, "⛔ وصول محدود!\nيجب عليك مشاهدة فيديو القرآن واستخراج الكود المائي منه أولاً.", reply_markup=markup)
        return

    # فحص إذا كان هناك تحميل سابق
    url_hash = hashlib.md5(url.encode()).hexdigest()[:10]
    file_id = f"{user_id}_{url_hash}"

    # تخزين مؤقت للمهمة
    data = Database.load()
    data["users"][str(user_id)] = {"url": url, "file_id": file_id}
    Database.save(data)

    # التحقق من وجود ملفات جزئية (.part)
    partial_path = f"{BASE_DIR}/{file_id}.mp4.part"
    if os.path.exists(partial_path):
        size = os.path.getsize(partial_path) / (1024*1024)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(f"✅ إكمال التحميل ({size:.1f}MB)", callback_data=f"resume_{user_id}_{file_id}"))
        markup.add(types.InlineKeyboardButton("❌ حذف والبدء من جديد", callback_data=f"restart_{user_id}_{file_id}"))
        bot.reply_to(message, "🔍 كشف استكمال:\nلقد وجدت جزءاً من هذا الفيديو محملاً مسبقاً، هل تريد الإكمال؟", reply_markup=markup)
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
        types.InlineKeyboardButton("🎵 MP3", callback_data=f"get_{user_id}_{file_id}_audio"),
        types.InlineKeyboardButton("⌨️ دقة يدوية", callback_data=f"manual_{user_id}_{file_id}")
    ]
    markup.add(*btns)
    bot.send_message(chat_id, "🎬 اختر الدقة المناسبة لسرعة إنترنتك:", reply_markup=markup)
    

#==========================================

#🔘 معالج الأزرار (Callbacks)

#==========================================

#==========================================
# 🔘 معالج الأزرار (Callbacks)
#==========================================

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    data = call.data.split('_')
    action = data[0]
    owner_id = data[1]

    # التأكد أن من ضغط الزر هو صاحب الطلب
    if not is_owner(call, owner_id): 
        return

    if action == "verify":
        msg = bot.send_message(call.message.chat.id, "🔢 أدخل الكود المائي المكون من 4 أرقام:")
        bot.register_next_step_handler(msg, check_verification_code)

    elif action == "get":
        file_id, quality = data[2], data[3]
        initiate_download(call.message, owner_id, file_id, quality)

    elif action == "manual":
        file_id = data[2]
        msg = bot.send_message(call.message.chat.id, "🔢 اكتب الدقة المطلوبة (رقم فقط مثل 240):")
        bot.register_next_step_handler(msg, lambda m: manual_dl_step(m, owner_id, file_id))

    elif action == "resume":
        file_id = data[2]
        # استكمال التحميل بجودة تلقائية 720
        initiate_download(call.message, owner_id, file_id, "720")

    elif action == "restart":
        file_id = data[2]
        # تنظيف الملفات القديمة قبل البدء من جديد
        for f in os.listdir(BASE_DIR):
            if file_id in f: 
                os.remove(os.path.join(BASE_DIR, f))
        show_quality_options(call.message.chat.id, owner_id, file_id)

#==========================================
# ⚙️ منطق التنفيذ النهائي (Final Execution)
#==========================================

def check_verification_code(message):
    if message.text == VERIFICATION_CODE:
        Database.verify_user(message.from_user.id)
        bot.reply_to(message, "✅ تم التحقق بنجاح! يمكنك الآن استخدام كافة ميزات البوت.")
    else:
        bot.reply_to(message, "❌ الكود خاطئ! شاهد الفيديو بتركيز لاستخراج الكود.")

def manual_dl_step(message, user_id, file_id):
    if message.text.isdigit():
        initiate_download(message, user_id, file_id, message.text)
    else:
        bot.reply_to(message, "⚠️ يرجى إدخال أرقام فقط.")

def initiate_download(message, user_id, file_id, quality):
    data_store = Database.load()
    task_data = data_store.get("users", {}).get(str(user_id))
    
    if not task_data: 
        bot.send_message(message.chat.id, "❌ خطأ في العثور على بيانات المهمة. أعد إرسال الرابط.")
        return

    url = task_data["url"]
    ext = "mp3" if quality == "audio" else "mp4"
    file_path = f"{BASE_DIR}/{file_id}.{ext}"

    prog_msg = bot.send_message(message.chat.id, "⏳ جاري تحضير الرابط والسيرفر...")

    # تشغيل في خلفية ThreadPool لضمان عدم توقف البوت
    executor.submit(run_task, prog_msg, user_id, url, quality, file_path)

def run_task(prog_msg, user_id, url, quality, file_path):
    dl = SmartDownloader(prog_msg.chat.id, prog_msg.message_id, user_id)
    success = dl.download(url, quality, file_path)

    if success is True:
        try:
            bot.edit_message_text("📤 اكتمل التحميل! جاري الرفع الآن...", prog_msg.chat.id, prog_msg.message_id)
            with open(file_path, 'rb') as f:
                if "audio" in quality:
                    bot.send_audio(prog_msg.chat.id, f, caption="🎵 تم التحميل بنجاح", timeout=1000)
                else:
                    bot.send_video(prog_msg.chat.id, f, caption="🎬 تم التحميل بنجاح", timeout=2000)

            # تنظيف المساحة بعد الرفع بنجاح
            if os.path.exists(file_path): 
                os.remove(file_path)
            
            try:
                bot.delete_message(prog_msg.chat.id, prog_msg.message_id)
            except:
                pass
            
        except Exception as e:
            bot.send_message(prog_msg.chat.id, f"❌ حدث خطأ أثناء الرفع: {e}")
    else:
        bot.edit_message_text(f"❌ فشل التحميل:\n{success}", prog_msg.chat.id, prog_msg.message_id)

# السطر الأخير لتشغيل البوت بشكل مستمر
# ==========================================
# 🏁 تشغيل المحرك النهائي
# ==========================================

if __name__ == "__main__":
    try:
        print("🚀 جاري تشغيل الأداة المتطورة...")
        # التأكد من تشغيل سيرفر Flask أولاً
        print("🌐 سيرفر Flask نشط على المنفذ 8080")
        
        # بدء استطلاع الرسائل (Polling)
        bot.infinity_polling(timeout=90, long_polling_timeout=5)
        
    except Exception as e:
        print(f"⚠️ حدث خطأ غير متوقع في المحرك الرئيسي: {e}")
        time.sleep(5)
        
