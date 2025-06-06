# ✅ Bot: yuklab olish + telegramga yuborish (fayl sifatida) + progress + tarix + tugmalar

import telebot
import requests
import os
import time
from threading import Thread
from telebot import types
import tempfile
import re
from collections import defaultdict

BOT_TOKEN = os.getenv("BOT_TOKEN") or '8015493310:AAHY_qlUtnejd_mIusC1GfhsAJdzzty6C6c'
ADMIN_ID = int(os.getenv("ADMIN_ID") or 1790455114)

bot = telebot.TeleBot(BOT_TOKEN)
progress_message_id = {}
cancel_flags = {}
user_history = defaultdict(list)

# ✅ Fayl nomini xavfsiz qilish
def sanitize_filename(filename):
    return re.sub(r'[^a-zA-Z0-9_.-]', '_', filename)

# ✅ Fayl yuklab olish funksiyasi (progress bilan)
def download_file_with_progress(url, file_path, chat_id):
    with requests.get(url, stream=True) as r:
        total_length = int(r.headers.get('content-length', 0))
        downloaded = 0
        start_time = time.time()
        with open(file_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                if cancel_flags.get(chat_id):
                    raise Exception("🚫 Yuklash foydalanuvchi tomonidan bekor qilindi.")
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    percent = int(downloaded * 100 / total_length)
                    elapsed = time.time() - start_time
                    speed = downloaded / 1024 / elapsed  # KB/s
                    eta = (total_length - downloaded) / 1024 / speed if speed > 0 else 0
                    progress_message = f"⬇️ Yuklanmoqda: {percent}%\n⏱ Tezlik: {speed:.2f} KB/s\n⏳ Qolgan vaqt: {eta:.1f} s"
                    try:
                        bot.edit_message_text(chat_id=chat_id, message_id=progress_message_id[chat_id], text=progress_message, reply_markup=get_cancel_keyboard())
                    except:
                        pass

# ✅ Faylni hujjat sifatida yuborish
def send_file(chat_id, file_path, caption):
    with open(file_path, 'rb') as f:
        bot.send_document(chat_id, f, caption=caption)

# ✅ Inline tugmalar
def get_inline_keyboard():
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("🔁 Yana yuklash", callback_data="reload"),
        types.InlineKeyboardButton("🗑 Tozalash", callback_data="clear")
    )
    return markup

# ✅ Yuklanish vaqtida bekor qilish tugmasi
def get_cancel_keyboard():
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel")
    )
    return markup

# ✅ /start komandasi
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('/start', '/history', '/files')
    return markup

@bot.message_handler(commands=['start'])
def handle_start(message):
    bot.send_message(message.chat.id, "🎬 MP4 URL yuboring, men yuklab, sizga fayl ko‘rinishida yuboraman.", reply_markup=main_menu())

# ✅ /history komandasi
@bot.message_handler(commands=['history'])
def handle_history(message):
    history = user_history.get(message.chat.id, [])
    if not history:
        bot.send_message(message.chat.id, "📭 Siz hali hech qanday fayl yubormagansiz.")
    else:
        msg = "🕓 Oxirgi yuborilgan fayllar:\n" + "\n".join(f"• {f}" for f in history[-5:])
        bot.send_message(message.chat.id, msg)

# ✅ /files komandasi
@bot.message_handler(commands=['files'])
def handle_files(message):
    bot.send_message(message.chat.id, "📂 Fayllar serverda saqlanmaydi. Har bir yuborishdan so‘ng o‘chiriladi.")

# ✅ MP4 URL qabul qilish
@bot.message_handler(func=lambda message: message.text and message.text.lower().endswith('.mp4'))
def handle_mp4_url(message):
    url = message.text.strip()
    raw_name = url.split('/')[-1]
    filename = sanitize_filename(raw_name)
    file_path = os.path.join(tempfile.gettempdir(), filename)
    chat_id = message.chat.id
    cancel_flags[chat_id] = False

    status = bot.send_message(chat_id, f"🔁 Yuklash boshlandi... 0%", reply_markup=get_cancel_keyboard())
    progress_message_id[chat_id] = status.message_id

    def process():
        try:
            download_file_with_progress(url, file_path, chat_id)
            caption = f"✅ Yuklash tugadi\n📂 Fayl: {filename}\n📦 Hajm: {os.path.getsize(file_path) / (1024*1024):.2f} MB"
            send_file(chat_id, file_path, caption)
            user_history[chat_id].append(filename)
            bot.send_message(chat_id, "🎉 Tayyor!", reply_markup=get_inline_keyboard())
        except Exception as e:
            bot.send_message(chat_id, f"❌ Xatolik: {str(e)}")
        finally:
            cancel_flags[chat_id] = False
            if os.path.exists(file_path):
                os.remove(file_path)

    Thread(target=process).start()

# ✅ Inline tugmalar uchun callback
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    if call.data == "reload":
        bot.send_message(call.message.chat.id, "🔁 Iltimos, URL ni qaytadan yuboring.")
    elif call.data == "clear":
        bot.send_message(call.message.chat.id, "🗑 Tozalandi.")
    elif call.data == "cancel":
        cancel_flags[call.message.chat.id] = True
        bot.send_message(call.message.chat.id, "❌ Yuklanish bekor qilindi.")

print("🤖 Bot ishga tushdi")
bot.infinity_polling()
