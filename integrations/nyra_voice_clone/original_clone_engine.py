import requests
import os,user_agent
import json
import telebot
import time
import re
from urllib.parse import quote
from datetime import datetime, timedelta
from user_agent import generate_user_agent
#-#-#-#-#-#-#-#-##-#-#-#-#-
token = "8754492132:AAFuNLUMIGXvzn0tGNGJ7qDV70xI-19e4kc"
id = "7012092596"
#-#-#-#-#-##-##-#-#-#-#-#
db_file_path = "uploaded_audios.json"
base_url = "https://voiceslab.io"
temp_api_url = "https://api.internal.temp-mail.io/api/v3"
http_session = requests.Session()
user_agent_default = generate_user_agent()
email_wait_timeout = 90
poll_delay_seconds = 3
auth_session_file = "sessions.json"

admin_telegram_id = id
settings_file_path = "bot_settings.json"
channels_file_path = "forced_channels.json"
stats_file_path = "bot_stats.json"

def load_settings():
    default_settings = {"status": "free", "paid_users": {}, "admins": [str(admin_telegram_id)], "trial_uses": {}}
    if not os.path.exists(settings_file_path):
        return default_settings
    try:
        with open(settings_file_path, "r") as f:
            settings = json.load(f)
            if "paid_users" not in settings:
                settings["paid_users"] = {}
            if "admins" not in settings:
                settings["admins"] = [str(admin_telegram_id)]
            if "trial_uses" not in settings:
                settings["trial_uses"] = {}
            return settings
    except:
        return default_settings

def save_settings(settings_data):
    with open(settings_file_path, "w") as f:
        json.dump(settings_data, f, indent=2)

def load_forced_channels():
    if not os.path.exists(channels_file_path):
        return []
    try:
        with open(channels_file_path, "r") as f:
            return json.load(f)
    except:
        return []

def save_forced_channels(channels_list):
    with open(channels_file_path, "w") as f:
        json.dump(channels_list, f, indent=2)

def load_bot_statistics():
    if not os.path.exists(stats_file_path):
        return {"total_users": 0, "usage_count": 0, "users": {}}
    try:
        with open(stats_file_path, "r") as f:
            return json.load(f)
    except:
        return {"total_users": 0, "usage_count": 0, "users": {}}
#ابوسك وتحبني؟
def save_bot_statistics(stats_data):
    with open(stats_file_path, "w") as f:
        json.dump(stats_data, f, indent=2)

def update_user_stats(user_id):
    stats_data = load_bot_statistics()
    user_id_str = str(user_id)
    
    if user_id_str not in stats_data["users"]:
        stats_data["users"][user_id_str] = {"first_seen": time.time(), "usage": 0}
        stats_data["total_users"] = len(stats_data["users"])
    
    stats_data["usage_count"] += 1
    stats_data["users"][user_id_str]["usage"] += 1
    save_bot_statistics(stats_data)

def check_user_quotas(cookie_header):
    url = "https://voiceslab.io/api/get-user-info"
    headers = {
        'User-Agent': str(user_agent.generate_user_agent()),
        'content-length': "0",
        'sec-ch-ua': "\"Chromium\";v=\"137\", \"Not/A)Brand\";v=\"24\"",
        'sec-ch-ua-platform': "\"Android\"",
        'sec-ch-ua-mobile': "?1",
        'content-type': "application/json",
        'origin': "https://voiceslab.io",
        'sec-fetch-site': "same-origin",
        'sec-fetch-mode': "cors",
        'sec-fetch-dest': "empty",
        'referer': "https://voiceslab.io/ar/dashboard/voice-cloning",
        'accept-language': "ar-EG,ar;q=0.9,en-US;q=0.8,en;q=0.7",
        'Cookie': cookie_header}

    response = requests.post(url, headers=headers)
    data = response.json()
    left_credits = data["data"]["clone_credits"]["left_credits"]

    if left_credits < 50:
        if os.path.exists("sessions.json"):
            os.remove("sessions.json")
            return True
    else:
        return False

def load_audio_cache():
    return json.load(open(db_file_path, "r")) if os.path.exists(db_file_path) else {}

def save_audio_cache(db_data):
    json.dump(db_data, open(db_file_path, "w"), indent=2)

def delete_voice(voice_id, cookie_header):
    url = f"https://voiceslab.io/api/clonevoices/{voice_id}"
    headers = {
        "User-Agent": user_agent.generate_user_agent(),
        "sec-ch-ua": "\"Chromium\";v=\"137\", \"Not/A)Brand\";v=\"24\"",
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": "\"Android\"",
        "origin": "https://voiceslab.io",
        "referer": "https://voiceslab.io/ar/dashboard/text-to-speech",
        "accept-language": "ar",
        "Cookie": cookie_header}
    try:
        r = requests.delete(url, headers=headers)
        return r.json().get("message") == "Voice deleted successfully"
    except:
        return False

def load_auth_session():
    if not os.path.exists(auth_session_file):
        return None
    try:
        with open(auth_session_file, "r", encoding="utf8") as f:
            data = json.load(f)
        cookies = data.get("cookies", {})
        if "__Secure-next-auth.session-token" in cookies:
            return data
        return None
    except Exception:
        return None

def save_auth_session(data):
    with open(auth_session_file, "w", encoding="utf8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def create_new_temp_email():
    r = requests.post(
        f"{temp_api_url}/email/new",
        headers={"User-Agent": user_agent_default, "Content-Type": "application/json"},
        json={"min_name_length": 10, "max_name_length": 10},
        timeout=15)
    r.raise_for_status()
    return r.json().get("email")

def fetch_csrf_token():
    r = http_session.get(
        f"{base_url}/api/auth/csrf",
        headers={"User-Agent": user_agent_default, "Accept": "application/json"},
        timeout=15)
    r.raise_for_status()
    return r.json().get("csrfToken")

def start_email_signin(email_address, csrf_token):
    data = {
        "email": email_address,
        "callbackUrl": f"{base_url}/en/dashboard/voice-cloning",
        "redirect": "false",
        "lang": "en",
        "csrfToken": csrf_token,
        "json": "true"}
    return http_session.post(
        f"{base_url}/api/auth/signin/email",
        headers={
            "User-Agent": user_agent_default,
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"},
        data=data,
        allow_redirects=False,
        timeout=15)

def poll_for_callback(email_address, timeout=email_wait_timeout, poll=poll_delay_seconds):
    end_time = time.time() + timeout
    link_re = re.compile(r"https?://[^\s'\"<>]+")
    while time.time() < end_time:
        r = requests.get(
            f"{temp_api_url}/email/{email_address}/messages",
            headers={"User-Agent": user_agent_default}, timeout=15)
        if r.ok:
            messages = r.json()
            for m in messages:
                text = (m.get("body_text") or "") + "\n" + (m.get("body_html") or "")
                match_link = link_re.search(text)
                if match_link:
                    link = match_link.group(0).replace("&amp;", "&")
                    if ("callback" in link) or ("token=" in link):
                        return link
        time.sleep(poll)
    raise TimeoutError("لم يصل رابط التفعيل خلال المهلة المحددة.")

def follow_and_check(link):
    r = http_session.get(
        link,
        headers={"User-Agent": user_agent_default, "Referer": base_url + "/"},
        allow_redirects=True,
        timeout=20)
    cookies = {
        k: v for k, v in http_session.cookies.items()
        if "next-auth" in k.lower() or "session" in k.lower()}
    return r, cookies

def ensure_authenticated_session():
    saved_session = load_auth_session()
    if saved_session:
        return saved_session
    email_address = create_new_temp_email()
    csrf_token = fetch_csrf_token()
    start_email_signin(email_address, csrf_token)
    login_link = poll_for_callback(email_address)
    response, session_cookies = follow_and_check(login_link)
    result = {
        "email": email_address,
        "verify_link": login_link,
        "final_url": response.url,
        "status": response.status_code,
        "cookies": session_cookies}
    save_auth_session(result)
    return result

def upload_voice_file(audio_path):
    session_data = ensure_authenticated_session()
    cookie_header = "; ".join([f"{k}={v}" for k, v in session_data["cookies"].items()])
    if check_user_quotas(cookie_header):
        session_data = ensure_authenticated_session()
        cookie_header = "; ".join([f"{k}={v}" for k, v in session_data["cookies"].items()])
        
    audio_cache = load_audio_cache()
    if audio_path in audio_cache:
        return True, audio_cache[audio_path]["voiceId"], cookie_header
    
    for old_path, old_data in list(audio_cache.items()):
        delete_voice(old_data["voiceId"], cookie_header)
    audio_cache = {}
    
    url = "https://voiceslab.io/api/create-voice"
    payload = {"title": "test", "language": "ar"}
    headers = {
        "User-Agent": user_agent.generate_user_agent(),
        "origin": "https://voiceslab.io",
        "referer": "https://voiceslab.io/ar/dashboard/voice-cloning",
        "accept-language": "ar",
        "Cookie": cookie_header}
    try:
        with open(audio_path, "rb") as f:
            files = [("audio", ("audio.mp3", f, "audio/mpeg"))]
            r = requests.post(url, data=payload, files=files, headers=headers)
        voice_id = r.json().get("voiceId")
        if not voice_id:
            return False, False, False
        audio_cache[audio_path] = {"voiceId": voice_id}
        save_audio_cache(audio_cache)
        return True, voice_id, cookie_header
    except:
        return False, False, False

def synthesize_text_to_audio(input_text, audio_path):
    success, voice_id, cookie_header = upload_voice_file(audio_path)
    if success == False:
        return success
    url = "https://voiceslab.io/api/clone-voice"
    payload = {
        "text": input_text,
        "voiceId": voice_id,
        "isPublicVoice": False,
        "settings": {
            "rate": 0,
            "volume": 0,
            "pitch": 0}}

    headers = {
        'User-Agent': str(user_agent.generate_user_agent()),
        'Content-Type': "application/json",
        'sec-ch-ua': "\"Chromium\";v=\"137\", \"Not/A)Brand\";v=\"24\"",
        'sec-ch-ua-platform': "\"Android\"",
        'sec-ch-ua-mobile': "?1",
        'origin': "https://voiceslab.io",
        'sec-fetch-site': "same-origin",
        'sec-fetch-mode': "cors",
        'sec-fetch-dest': "empty",
        'referer': "https://voiceslab.io/ar/dashboard/text-to-speech",
        'accept-language': "ar-EG,ar;q=0.9,en-US;q=0.8,en;q=0.7",
        'Cookie': cookie_header}
    response = requests.post(url, data=json.dumps(payload), headers=headers)
    try:
        return response.json()["audioUrl"]
    except:
        return False
#بس فلان ليش سويه هيج؟
bot = telebot.TeleBot(token)
current_voice_path = None
channel_add_state = {}
cloning_state = {}
broadcast_state = set()
user_activation_state = {}

def clear_old_voice():
    for f in os.listdir("."):
        if f.endswith(".mp3") and f.startswith("voice_"):
            try:
                os.remove(f)
            except:
                pass

def save_telegram_audio(file_info):
    global current_voice_path
    clear_old_voice()
    downloaded = bot.download_file(file_info.file_path)
    timestamp = int(time.time() * 1000)
    current_voice_path = f"voice_{timestamp}.mp3"
    with open(current_voice_path, "wb") as f:
        f.write(downloaded)
    return current_voice_path

def is_admin(user_id, settings_data=None):
    settings_data = settings_data or load_settings()
    return str(user_id) == str(admin_telegram_id) or str(user_id) in [str(x) for x in settings_data.get("admins", [])]

def premium_active(user_id, settings_data):
    item = settings_data.get("paid_users", {}).get(str(user_id))
    if item is True:
        return True
    if isinstance(item, dict):
        if item.get("plan") == "vip":
            return True
        expires = item.get("expires_at")
        if expires:
            try:
                return datetime.fromisoformat(expires) > datetime.now()
            except Exception:
                return False
    return False

def trial_left(user_id, settings_data):
    return max(0, 3 - int(settings_data.get("trial_uses", {}).get(str(user_id), 0)))

def is_user_authorized(user_id, settings_data):
    if is_admin(user_id, settings_data) or premium_active(user_id, settings_data):
        return True
    return settings_data.get("status", "free") == "free" and trial_left(user_id, settings_data) > 0

def consume_trial(user_id):
    settings_data = load_settings()
    if is_admin(user_id, settings_data) or premium_active(user_id, settings_data):
        return True
    if settings_data.get("status", "free") != "free":
        return False
    left = trial_left(user_id, settings_data)
    if left <= 0:
        return False
    settings_data.setdefault("trial_uses", {})[str(user_id)] = int(settings_data["trial_uses"].get(str(user_id), 0)) + 1
    save_settings(settings_data)
    return True

def admin_panel_markup(settings_data):
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    status = settings_data.get("status", "free")
    toggle_text = "💰 البوت مدفوع (اضغط للتحويل إلى مجاني)" if status == "paid" else "🆓 البوت مجاني (اضغط للتحويل إلى مدفوع)"
    
    markup.add(
        telebot.types.InlineKeyboardButton(toggle_text, callback_data=f"toggle_status_{status}"),
        telebot.types.InlineKeyboardButton("⚙️ تفعيل/إلغاء تفعيل مستخدم", callback_data="manage_paid_users"),
        telebot.types.InlineKeyboardButton("📊 عرض إحصائيات البوت", callback_data="show_stats"),
        telebot.types.InlineKeyboardButton("➕ إدارة قنوات الإشتراك الإجباري", callback_data="manage_channels"),
        telebot.types.InlineKeyboardButton("💎 تفعيل اشتراك بمدة", callback_data="prompt_subscription"),
        telebot.types.InlineKeyboardButton("👑 إدارة الأدمن", callback_data="manage_admins")
    )
    return markup
#ليشش اريد افهممم؟
def subscription_markup(user_id):
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    plans = [
        ("💎 اشتراك يوم — 10 جنيه", "day", "10 جنيه"),
        ("💎 اشتراك أسبوع — 30 جنيه", "week", "30 جنيه"),
        ("💎 اشتراك شهر — 70 جنيه", "month", "70 جنيه"),
        ("💎 اشتراك سنة — 300 جنيه", "year", "300 جنيه"),
        ("👑 VIP — غير محدود", "vip", "حسب الاتفاق"),
    ]
    for title, plan, price in plans:
        msg = (f"السلام عليكم، أنا أريد {title}\n"
               f"ID المستخدم: {user_id}\n"
               f"من فضلك وضّح طريقة الدفع والتفعيل.")
        url = "https://t.me/A_A_Q5?text=" + quote(msg)
        markup.add(telebot.types.InlineKeyboardButton(title, url=url))
    markup.add(telebot.types.InlineKeyboardButton("👨‍💻 التواصل مع المطور", url="https://t.me/A_A_Q5"))
    return markup

def send_subscription_required(chat_id, user_id):
    text = (
        "⛔ انتهى رصيد المحاولات المجانية أو أن الاشتراك غير مفعل.\n\n"
        "📌 لتفعيل البوت، اختر الاشتراك المناسب من القائمة التالية.\n"
        "سيتم فتح محادثة المطور برسالة جاهزة تحتوي على الاشتراك الذي اخترته.\n\n"
        "👨‍💻 المطور: @A_A_Q5"
    )
    bot.send_message(chat_id, text, reply_markup=subscription_markup(user_id))

def user_welcome_markup():
    markup = telebot.types.InlineKeyboardMarkup()
    clone_button = telebot.types.InlineKeyboardButton("استنساخ الصوت", callback_data='start_clone')
    dev_button = telebot.types.InlineKeyboardButton("المطور", url="https://t.me/A_A_Q5")
    markup.row(clone_button, dev_button)
    return markup

def check_subscription(user_id):
    channels = load_forced_channels()
    if not channels:
        return True, None
    
    not_subscribed_channels = []
    for channel in channels:
        try:
            member = bot.get_chat_member(chat_id=channel["id"], user_id=user_id)
            if member.status in ['left', 'kicked']:
                not_subscribed_channels.append(channel)
        except Exception:
            pass

    if not not_subscribed_channels:
        return True, None
    
    markup = telebot.types.InlineKeyboardMarkup()
    for channel in not_subscribed_channels:
        display_name = channel.get("name", f"@{channel['username']}")
        markup.add(telebot.types.InlineKeyboardButton(display_name, url=f"https://t.me/{channel['username']}"))
    markup.add(telebot.types.InlineKeyboardButton("✅ تحقق من الإشتراك", callback_data="check_sub"))
    
    return False, markup



@bot.message_handler(commands=['m'])
def start_broadcast(message):
    user_id = message.from_user.id
    if not is_admin(user_id, load_settings()):
        bot.reply_to(message, "❌ الأمر ده متاح للأدمن فقط.")
        return
    broadcast_state.add(user_id)
    bot.reply_to(message, "📢 ابعت الآن الرسالة أو الصورة أو الفيديو أو الملف اللي عايز تبعته لكل المستخدمين.")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    settings_data = load_settings()
    user_name = message.from_user.first_name if message.from_user.first_name else "صديقنا"

    if is_admin(user_id, settings_data):
        bot.send_message(
            user_id,
            "لوحة تحكم الأدمن:",
            reply_markup=admin_panel_markup(settings_data))
        
    
    is_subscribed, sub_markup = check_subscription(user_id)
    if not is_subscribed:
        bot.send_message(
            user_id,
            "يجب عليك الاشتراك في القنوات التالية لاستخدام البوت:",
            reply_markup=sub_markup)
        return

    if not is_user_authorized(user_id, settings_data):
        send_subscription_required(message.chat.id, user_id)
        return

    remaining = "غير محدود" if (is_admin(user_id, settings_data) or premium_active(user_id, settings_data)) else str(trial_left(user_id, settings_data))
    welcome_message = (
        f"🎙️ أهلاً بك في بوت استنساخ الأصوات (⫷ دلـوعـة ⫸)\n\n"
        f"👤 المستخدم: {user_name}\n"
        f"⏱️ مدة الصوت: من 10 إلى 30 ثانية\n"
        f"📩 أرسل الصوتية أولاً، ثم أرسل النص المطلوب نطقه\n"
        f"🎁 المحاولات المتبقية: {remaining}\n\n"
        f"👨‍💻 المطور: @A_A_Q5")
    bot.send_message(message.chat.id, welcome_message, reply_markup=user_welcome_markup())



@bot.message_handler(content_types=['photo', 'video', 'document', 'animation', 'sticker'])
def handle_broadcast_media(message):
    user_id = message.from_user.id
    if user_id not in broadcast_state:
        return
    if not is_admin(user_id, load_settings()):
        broadcast_state.discard(user_id)
        return
    stats_data = load_bot_statistics()
    users = list(stats_data.get("users", {}).keys())
    sent = failed = 0
    bot.reply_to(message, f"📤 جاري إرسال الإعلان إلى {len(users)} مستخدم...")
    for target_id in users:
        try:
            bot.copy_message(int(target_id), message.chat.id, message.message_id)
            sent += 1
            time.sleep(0.05)
        except Exception:
            failed += 1
    broadcast_state.discard(user_id)
    bot.send_message(message.chat.id, f"✅ انتهى الإرسال\nتم بنجاح: {sent}\nفشل: {failed}")

@bot.message_handler(content_types=['audio', 'voice'])
def handle_audio_voice(message):
    global current_voice_path
    user_id = message.from_user.id
    settings_data = load_settings()

    if not is_user_authorized(user_id, settings_data):
        return

    is_subscribed, sub_markup = check_subscription(user_id)
    if not is_subscribed:
        bot.reply_to(message, "يجب عليك الاشتراك في القنوات المطلوبة أولا.")
        return

    if cloning_state.get(user_id) != 'waiting_for_audio':
        bot.reply_to(message, "يرجى الضغط على زر 'استنساخ الصوت' أولا لبدء العملية.")
        return

    media = message.audio if message.audio else message.voice
    
    if message.audio and media.mime_type != "audio/mpeg":
        bot.reply_to(message, "أرسل فقط ملفات mp3.")
        return
        
    if media.duration < 10 or media.duration > 30:
        bot.reply_to(message, "الصوت يجب أن يكون بين 10 و30 ثانية.")
        return
        
    file_info = bot.get_file(media.file_id)
    save_telegram_audio(file_info)
    cloning_state[user_id] = 'waiting_for_text'
    bot.reply_to(message, "تم استلام الصوتية.\nالان ارسل النص المراد استنساخه.")

@bot.message_handler(content_types=['text'])
def handle_text(message):
    global current_voice_path
    user_id = message.from_user.id
    text = message.text
    settings_data = load_settings()
    
    if is_admin(user_id, settings_data):
        if user_id in channel_add_state:
            try:
                channel_username = text.strip().lstrip('@')
                chat = bot.get_chat(f"@{channel_username}")
                
                channels = load_forced_channels()
                channel_exists = any(c['username'] == channel_username for c in channels)
                
                if channel_exists:
                    bot.reply_to(message, "القناة مضافة بالفعل.")
                else:
                    channels.append({"id": chat.id, "username": channel_username, "name": chat.title})
                    save_forced_channels(channels)
                    bot.reply_to(message, f"تم إضافة القناة {chat.title} بنجاح.")
            except Exception as e:
                bot.reply_to(message, "حدث خطأ. تأكد من صحة معرف القناة وأن البوت مشرف فيها.")
            
            del channel_add_state[user_id]
            return
        
        if user_id in user_activation_state:
            try:
                target_user_id = int(text.strip())
                settings_data = load_settings()
                
                action = user_activation_state[user_id]
                target_user_id_str = str(target_user_id)

                if action == "subscription":
                    parts = text.strip().split()
                    if len(parts) != 2:
                        raise ValueError()
                    target_user_id = int(parts[0])
                    duration = parts[1].lower()
                    if duration == "vip":
                        settings_data["paid_users"][str(target_user_id)] = {"plan": "vip"}
                    else:
                        days = {"day": 1, "week": 7, "month": 30, "year": 365}.get(duration)
                        if not days:
                            raise ValueError()
                        settings_data["paid_users"][str(target_user_id)] = {"plan": duration, "expires_at": (datetime.now() + timedelta(days=days)).isoformat()}
                    save_settings(settings_data)
                    bot.reply_to(message, "تم تفعيل الاشتراك بنجاح.")
                    del user_activation_state[user_id]
                    return

                if action == "admin_add":
                    parts = text.strip().split()
                    if parts[0].lower() == "remove" and len(parts) == 2:
                        settings_data["admins"] = [x for x in settings_data.get("admins", []) if str(x) != parts[1]]
                    else:
                        settings_data.setdefault("admins", []).append(str(int(parts[0])))
                    save_settings(settings_data)
                    bot.reply_to(message, "تم تحديث قائمة الأدمن.")
                    del user_activation_state[user_id]
                    return
                
                if action == 'activate':
                    settings_data['paid_users'][target_user_id_str] = True
                    msg = f"تم تفعيل البوت للمستخدم ID: {target_user_id}."
                elif action == 'deactivate':
                    if target_user_id_str in settings_data['paid_users']:
                        del settings_data['paid_users'][target_user_id_str]
                    msg = f"تم إلغاء تفعيل البوت للمستخدم ID: {target_user_id}."
                
                save_settings(settings_data)
                bot.reply_to(message, msg)
                
            except ValueError:
                bot.reply_to(message, "الرجاء إدخال رقم ID صحيح.")
            except Exception:
                bot.reply_to(message, "حدث خطأ أثناء معالجة العملية.")
            
            del user_activation_state[user_id]
            return

    if user_id in broadcast_state:
        if not is_admin(user_id, load_settings()):
            broadcast_state.discard(user_id)
            return
        stats_data = load_bot_statistics()
        users = list(stats_data.get("users", {}).keys())
        sent = 0
        failed = 0
        bot.reply_to(message, f"📤 جاري إرسال الإعلان إلى {len(users)} مستخدم...")
        for target_id in users:
            try:
                bot.copy_message(int(target_id), message.chat.id, message.message_id)
                sent += 1
                time.sleep(0.05)
            except Exception:
                failed += 1
        broadcast_state.discard(user_id)
        bot.send_message(message.chat.id, f"✅ انتهى الإرسال\nتم بنجاح: {sent}\nفشل: {failed}")
        return

    settings_data = load_settings()
    if not is_user_authorized(user_id, settings_data):
        return

    is_subscribed, sub_markup = check_subscription(user_id)
    if not is_subscribed:
        bot.reply_to(message, "يجب عليك الاشتراك في القنوات المطلوبة أولا.")
        return
    
    if cloning_state.get(user_id) != 'waiting_for_text':
        bot.reply_to(message, "أرسل أولاً ملف mp3 أو رسالة صوتية مناسبة بعد الضغط على زر 'استنساخ الصوت'.")
        return

    if not current_voice_path or not os.path.exists(current_voice_path):
        bot.reply_to(message, "حدث خطأ. يرجى إعادة إرسال الصوتية.")
        del cloning_state[user_id]
        return

    processing_msg = bot.reply_to(message, "جار استنساخ الصوت انتضر من فضلك .....")
    
    audio_url = synthesize_text_to_audio(text, current_voice_path)
    
    if audio_url is False:
        bot.edit_message_text("حدث خطأ في الاستنساخ.", message.chat.id, processing_msg.message_id)
        if user_id in cloning_state:
            del cloning_state[user_id]
        return
    
    if not consume_trial(user_id):
        bot.edit_message_text("انتهت المحاولات المجانية. راسل الأدمن لتفعيل اشتراك.", message.chat.id, processing_msg.message_id)
        if user_id in cloning_state:
            del cloning_state[user_id]
        return

    update_user_stats(user_id)
    bot.send_audio(chat_id=message.chat.id, audio=audio_url, caption=f"النص: {text}\nحساب المطور: @A_A_Q5 تلي")
    bot.edit_message_text("تم استنساخ الصوت", message.chat.id, processing_msg.message_id)
    if user_id in cloning_state:
        del cloning_state[user_id]

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    user_id = call.from_user.id
    data = call.data

    if data == 'check_sub':
        is_subscribed, sub_markup = check_subscription(user_id)
        if is_subscribed:
            bot.answer_callback_query(call.id, "✅ تم الإشتراك بنجاح! يمكنك الآن استخدام البوت.")
            send_welcome(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ لم يتم الإشتراك في جميع القنوات.")
        return

    if data == 'start_clone':
        settings_data = load_settings()
        if not is_user_authorized(user_id, settings_data):
            bot.answer_callback_query(call.id, "انتهت المحاولات المجانية")
            send_subscription_required(user_id, user_id)
            return

        cloning_state[user_id] = 'waiting_for_audio'
        bot.answer_callback_query(call.id, "الرجاء إرسال الصوتية الآن (بين 10-30 ثانية).")
        bot.send_message(user_id, "أرسل الصوتية المطلوبة:")
        return
    
    if not is_admin(user_id, load_settings()):
        bot.answer_callback_query(call.id, "أنت لست الأدمن.")
        return

    if data.startswith("toggle_status_"):
        current_status = data.split("_")[-1]
        new_status = "paid" if current_status == "free" else "free"
        settings_data = load_settings()
        settings_data["status"] = new_status
        save_settings(settings_data)
        
        status_text = "مدفوع" if new_status == "paid" else "مجاني"
        bot.edit_message_text(
            f"تم تغيير وضع البوت إلى: {status_text}",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=admin_panel_markup(settings_data))

    elif data == "manage_paid_users":
        settings_data = load_settings()
        paid_users = settings_data.get("paid_users", {})
        
        text = f"إدارة تفعيل المستخدمين:\n(مفعل حالياً: {len([uid for uid, status in paid_users.items() if status])} مستخدم)"
        
        markup = telebot.types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            telebot.types.InlineKeyboardButton("تفعيل مستخدم", callback_data="prompt_activate_user"),
            telebot.types.InlineKeyboardButton("إلغاء تفعيل مستخدم", callback_data="prompt_deactivate_user"),
            telebot.types.InlineKeyboardButton("رجوع للوحة الأدمن", callback_data="back_to_admin")
        )
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif data == "prompt_activate_user":
        user_activation_state[user_id] = 'activate'
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("إلغاء", callback_data="manage_paid_users"))
        bot.edit_message_text("أرسل الآن الـ User ID الذي تريد تفعيله:", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif data == "prompt_deactivate_user":
        user_activation_state[user_id] = 'deactivate'
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("إلغاء", callback_data="manage_paid_users"))
        bot.edit_message_text("أرسل الآن الـ User ID الذي تريد إلغاء تفعيله:", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif data == "show_stats":
        stats_data = load_bot_statistics()
        text = (
            f"📊 إحصائيات البوت:\n"
            f"عدد المستخدمين الكلي: {stats_data['total_users']}\n"
            f"عدد مرات الاستخدام الكلي: {stats_data['usage_count']}"
        )
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("رجوع للوحة الأدمن", callback_data="back_to_admin"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif data == "prompt_subscription":
        user_activation_state[user_id] = "subscription"
        bot.send_message(user_id, "أرسل بالصيغة: USER_ID مدة\nالمدة: day أو week أو month أو year أو vip")

    elif data == "manage_admins":
        user_activation_state[user_id] = "admin_add"
        bot.send_message(user_id, "أرسل ID الأدمن الجديد، أو اكتب remove ID للحذف.")

    elif data == "manage_channels":
        channels = load_forced_channels()
        markup = telebot.types.InlineKeyboardMarkup(row_width=1)
        
        if channels:
            markup.add(telebot.types.InlineKeyboardButton("عرض القنوات المضافة", callback_data="view_channels"))
            markup.add(telebot.types.InlineKeyboardButton("حذف قناة", callback_data="delete_channel_prompt"))

        markup.add(telebot.types.InlineKeyboardButton("إضافة قناة جديدة", callback_data="add_channel_prompt"))
        markup.add(telebot.types.InlineKeyboardButton("رجوع للوحة الأدمن", callback_data="back_to_admin"))
        
        bot.edit_message_text(
            "إدارة قنوات الإشتراك الإجباري:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup)

    elif data == "add_channel_prompt":
        channel_add_state[user_id] = True
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("إلغاء", callback_data="manage_channels"))
        bot.edit_message_text(
            "أرسل الآن معرف القناة (مثال: @channelusername). تأكد أن البوت مشرف فيها:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup)

    elif data == "view_channels":
        channels = load_forced_channels()
        if channels:
            text = "قنوات الإشتراك الإجباري:\n"
            for i, ch in enumerate(channels):
                ch_name = ch.get("name", f"@{ch['username']}")
                text += f"{i+1}. {ch_name} (@{ch['username']})\n"
        else:
            text = "لا توجد قنوات اشتراك مضافة حالياً."
        
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("رجوع لإدارة القنوات", callback_data="manage_channels"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif data == "delete_channel_prompt":
        channels = load_forced_channels()
        if not channels:
            bot.answer_callback_query(call.id, "لا توجد قنوات للحذف.")
            return
#ليش راجع راجع انته
        markup = telebot.types.InlineKeyboardMarkup(row_width=1)
        for i, ch in enumerate(channels):
            ch_name = ch.get("name", f"@{ch['username']}")
            markup.add(telebot.types.InlineKeyboardButton(
                f"حذف {ch_name}", 
                callback_data=f"delete_channel_confirm_{i}"))
        
        markup.add(telebot.types.InlineKeyboardButton("إلغاء", callback_data="manage_channels"))
        
        bot.edit_message_text(
            "اختر القناة المراد حذفها:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup)

    elif data.startswith("delete_channel_confirm_"):
        index = int(data.split("_")[-1])
        channels = load_forced_channels()
        
        if 0 <= index < len(channels):
            deleted_channel = channels.pop(index)
            save_forced_channels(channels)
            bot.answer_callback_query(call.id, f"تم حذف القناة {deleted_channel.get('name', deleted_channel['username'])} بنجاح.")
            
            if channels:
                callback_inline(telebot.types.CallbackQuery(id=call.id, from_user=call.from_user, data="delete_channel_prompt", message=call.message))
            else:
                callback_inline(telebot.types.CallbackQuery(id=call.id, from_user=call.from_user, data="manage_channels", message=call.message))
        else:
            bot.answer_callback_query(call.id, "خطأ في اختيار القناة.")

    elif data == "back_to_admin":
        settings_data = load_settings()
        bot.edit_message_text(
            "لوحة تحكم الأدمن:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=admin_panel_markup(settings_data))

if __name__ == '__main__':
    bot.infinity_polling()
###-#-#-#-#-#-#-#-#--##-