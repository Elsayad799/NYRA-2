import os
import re
import time
import json
import queue
import threading
import requests
import telebot
from telebot import types

#@FF_MZ
BOT_TOKEN = "NYRA_INTERNAL_SOURCE"
bot = telebot.TeleBot(BOT_TOKEN, threaded=True, num_threads=30)

#@FF_MZ
BASE_TEMPMAIL_URL = "https://api.internal.temp-mail.io/api/v3"
HEADERS = {"Content-Type": "application/json"}
PASSWORD = "admin#01"
TOKENS_FILE = "tokens_pool.json"

#@FF_MZ
user_sessions = {}
tokens_pool = queue.Queue()
pool_lock = threading.Lock()
generating_accounts_count = 0
last_error = None

#@FF_MZ
def load_tokens():
    #@FF_MZ
    if os.path.exists(TOKENS_FILE):
        try:
            with open(TOKENS_FILE, "r", encoding="utf-8") as f:
                tokens = json.load(f)
                for t in tokens:
                    tokens_pool.put(t)
        except Exception:
            pass

#@FF_MZ
def save_tokens():
    #@FF_MZ
    with pool_lock:
        tokens_list = list(tokens_pool.queue)
        with open(TOKENS_FILE, "w", encoding="utf-8") as f:
            json.dump(tokens_list, f)

#@FF_MZ
def create_email():
    #@FF_MZ
    url = f"{BASE_TEMPMAIL_URL}/email/new"
    payload = {"min_name_length": 10, "max_name_length": 10}
    try:
        response = requests.post(url, json=payload, headers=HEADERS, timeout=15)
        if response.status_code == 200:
            return response.json().get("email")
    except Exception:
        pass
    return None

#@FF_MZ
def fetch_messages(email):
    #@FF_MZ
    url = f"{BASE_TEMPMAIL_URL}/email/{email}/messages"
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return []

#@FF_MZ
def extract_otp(messages):
    #@FF_MZ
    for msg in messages:
        subject = msg.get("subject", "")
        body = msg.get("body_text") or msg.get("body_html") or msg.get("body") or ""
        full_text = f"{subject}\n{body}"
        match = re.search(r'\b\d{6}\b', full_text)
        if match:
            return match.group(0)
    return None

#@FF_MZ
def create_new_account():
    #@FF_MZ
    global generating_accounts_count
    with pool_lock:
        generating_accounts_count += 1

    try:
        email = create_email()
        if not email:
            return None

        session = requests.Session()
        session.headers.update({
            'Content-Type': "application/json",
            'referer': "https://app.banani.co/auth/signup",
        })

        #@FF_MZ
        signup_url = "https://app.banani.co/api/auth/sign-up/email"
        signup_payload = {
            "name": "",
            "email": email,
            "password": PASSWORD,
            "callbackURL": "/customize-experience"
        }
        session.post(signup_url, json=signup_payload, timeout=15)

        #@FF_MZ
        send_otp_url = "https://app.banani.co/api/auth/email-otp/send-verification-otp"
        send_otp_payload = {"email": email, "type": "email-verification"}
        session.post(send_otp_url, json=send_otp_payload, timeout=15)

        #@FF_MZ
        otp_code = None
        for _ in range(20):
            messages = fetch_messages(email)
            if messages:
                otp_code = extract_otp(messages)
                if otp_code:
                    break
            time.sleep(3)

        if not otp_code:
            return None

        #@FF_MZ
        verify_url = "https://app.banani.co/api/auth/email-otp/verify-email"
        verify_payload = {"email": email, "otp": otp_code}
        session.post(verify_url, json=verify_payload, timeout=15)

        #@FF_MZ
        signin_url = "https://app.banani.co/api/auth/sign-in/email"
        signin_payload = {
            "email": email,
            "password": PASSWORD,
            "callbackURL": "/customize-experience"
        }
        response = session.post(signin_url, json=signin_payload, timeout=15)

        session_token = response.cookies.get("__Secure-better-auth.session_token")
        if not session_token:
            try:
                session_token = response.json().get("token")
            except Exception:
                pass

        if session_token:
            tokens_pool.put(session_token)
            save_tokens()
            return session_token
    except Exception:
        pass
    finally:
        with pool_lock:
            generating_accounts_count -= 1
    return None

#@FF_MZ
def ensure_tokens_available(target_count=3):
    #@FF_MZ
    def worker():
        while tokens_pool.qsize() + generating_accounts_count < target_count:
            create_new_account()
    threading.Thread(target=worker, daemon=True).start()

#@FF_MZ
def get_token():
    #@FF_MZ
    ensure_tokens_available(target_count=3)
    try:
        return tokens_pool.get_nowait()
    except queue.Empty:
        return create_new_account()

#@FF_MZ
def generate_images_api(promt, aspect_ratio, count, max_retries=3):
    #@FF_MZ
    global last_error
    if max_retries <= 0:
        last_error = "generation retries exhausted"
        return None

    token = get_token()
    if not token:
        last_error = "no usable image-service session token is available"
        return None
    if not token:
        return None

    url = "https://app.banani.co/api/trpc/generation.generateImages"
    params = {'batch': "1"}
    payload = {
        "0": {
            "json": {
                "prompt": promt,
                "aspectRatio": aspect_ratio,
                "count": count
            }
        }
    }
    headers = {
        'User-Agent': "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
        'Content-Type': "application/json",
        'sec-ch-ua-platform': '"Linux"',
        'Cookie': f"__Secure-better-auth.session_token={token};"
    }

    try:
        response = requests.post(url, params=params, data=json.dumps(payload), headers=headers, timeout=60)
        if response.status_code == 200:
            res_data = response.json()
            images = res_data[0]["result"]["data"]["json"]["images"]
            if images and len(images) > 0:
                last_error = None
                tokens_pool.put(token)
                return images
            last_error = "image service returned HTTP 200 but no image URLs"
        else:
            last_error = f"image service HTTP {response.status_code}: {response.text[:300]}"
    except Exception as exc:
        last_error = f"image service request failed: {type(exc).__name__}: {exc}"
        log_msg = last_error
        try:
            print(f"[NYRA image source] {log_msg}")
        except Exception:
            pass

    #@FF_MZ
    ensure_tokens_available(target_count=3)
    return generate_images_api(promt, aspect_ratio, count, max_retries - 1)

#@FF_MZ
def animate_loading(chat_id, message_id, stop_event):
    #@FF_MZ
    frames = ["⏳ جاري إنشاء الصور", "⏳ جاري إنشاء الصور .", "⏳ جاري إنشاء الصور ..", "⏳ جاري إنشاء الصور ..."]
    seconds = 0
    idx = 0
    while not stop_event.is_set():
        time.sleep(2)
        if stop_event.is_set():
            break
        seconds += 2
        idx = (idx + 1) % len(frames)
        text = f"{frames[idx]}\n⏱️ الوقت المنقضي: {seconds} ثواني"
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=message_id)
        except Exception:
            pass

#@FF_MZ
@bot.message_handler(commands=['start'])
def send_welcome(message):
    #@FF_MZ
    markup = types.InlineKeyboardMarkup()
    dev_button = types.InlineKeyboardButton("المطور 👨‍💻", url="https://t.me/FF_MZ")
    markup.add(dev_button)
    
    bot.reply_to(
        message, 
        "اهلا بك ارسل البرومت / الوصف للبدأ في انشاء الصور ",
        reply_markup=markup
    )

#@FF_MZ
@bot.message_handler(func=lambda message: True)
def handle_promt(message):
    #@FF_MZ
    chat_id = message.chat.id
    user_sessions[chat_id] = {'promt': message.text}

    markup = types.InlineKeyboardMarkup(row_width=3)
    btn1 = types.InlineKeyboardButton("16:9", callback_data="ratio_16:9")
    btn2 = types.InlineKeyboardButton("9:16", callback_data="ratio_9:16")
    btn3 = types.InlineKeyboardButton("1:1", callback_data="ratio_1:1")
    btn4 = types.InlineKeyboardButton("4:3", callback_data="ratio_4:3")
    btn5 = types.InlineKeyboardButton("3:4", callback_data="ratio_3:4")
    
    markup.add(btn1, btn2, btn3)
    markup.add(btn4, btn5)

    bot.send_message(chat_id, "اختر مقاس الصورة المطلوب:", reply_markup=markup)

#@FF_MZ
@bot.callback_query_handler(func=lambda call: call.data.startswith("ratio_"))
def handle_ratio_choice(call):
    #@FF_MZ
    chat_id = call.message.chat.id
    if chat_id not in user_sessions:
        bot.answer_callback_query(call.id, "حدث خطأ، يرجى إرسال الـ Promt من جديد.")
        return

    aspect_ratio = call.data.split("_")[1]
    user_sessions[chat_id]['aspect_ratio'] = aspect_ratio

    markup = types.InlineKeyboardMarkup(row_width=4)
    btns = [types.InlineKeyboardButton(str(i), callback_data=f"count_{i}") for i in range(1, 5)]
    markup.add(*btns)

    bot.edit_message_text(
        "اختر عدد الصور المراد إنشاؤها (الحد الأقصى 4):",
        chat_id=chat_id,
        message_id=call.message.message_id,
        reply_markup=markup
    )

#@FF_MZ
@bot.callback_query_handler(func=lambda call: call.data.startswith("count_"))
def handle_count_choice(call):
    #@FF_MZ
    chat_id = call.message.chat.id
    if chat_id not in user_sessions:
        bot.answer_callback_query(call.id, "حدث خطأ، يرجى إرسال الـ Promt من جديد.")
        return

    count = int(call.data.split("_")[1])
    session_data = user_sessions[chat_id]
    promt = session_data['promt']
    aspect_ratio = session_data['aspect_ratio']

    msg = bot.edit_message_text(
        "⏳ جاري إنشاء الصور...",
        chat_id=chat_id,
        message_id=call.message.message_id
    )

    #@FF_MZ
    stop_event = threading.Event()
    anim_thread = threading.Thread(
        target=animate_loading, 
        args=(chat_id, msg.message_id, stop_event), 
        daemon=True
    )
    anim_thread.start()

    #@FF_MZ
    images = generate_images_api(promt, aspect_ratio, count)
    stop_event.set()

    if images:
        try:
            bot.delete_message(chat_id, msg.message_id)
        except Exception:
            pass
        
        media_group = [types.InputMediaPhoto(url) for url in images]
        bot.send_media_group(chat_id, media_group)
    else:
        try:
            bot.edit_message_text(
                "❌ حدث خطأ أثناء إنشاء الصور، يرجى المحاولة لاحقاً.",
                chat_id=chat_id,
                message_id=msg.message_id
            )
        except Exception:
            pass

    #@FF_MZ
    user_sessions.pop(chat_id, None)

#@FF_MZ
if __name__ == "__main__":
    pass
