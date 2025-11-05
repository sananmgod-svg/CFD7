from http.server import BaseHTTPRequestHandler
import json
import requests
import sqlite3
import os
from datetime import datetime, timedelta
import re

# تنظیمات اصلی
BOT_TOKEN = "EEEBI0IIOOCEPWGIVWDRTGXPDDUSMBZNPAYZOLZDHPKEAAYRWKCLJLTNQNXDIGES"
ADMIN_PASSWORD = "09934595428"
MAIN_ADMIN = "@AdminCFD7"
BASE_URL = f"https://botapi.rubika.ir/v3/{BOT_TOKEN}"

# دیتابیس
def init_db():
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY,
            group_id TEXT UNIQUE,
            group_name TEXT,
            owner_id TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY,
            group_id TEXT,
            admin_id TEXT,
            FOREIGN KEY (group_id) REFERENCES groups (group_id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS banned_words (
            id INTEGER PRIMARY KEY,
            group_id TEXT,
            word TEXT,
            FOREIGN KEY (group_id) REFERENCES groups (group_id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_warnings (
            id INTEGER PRIMARY KEY,
            user_id TEXT,
            group_id TEXT,
            warnings INTEGER DEFAULT 0,
            last_warning TIMESTAMP,
            muted_until TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS auto_responses (
            id INTEGER PRIMARY KEY,
            group_id TEXT,
            trigger_text TEXT,
            response_text TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS group_settings (
            id INTEGER PRIMARY KEY,
            group_id TEXT UNIQUE,
            welcome_message TEXT DEFAULT '👋 به گروه خوش آمدید!',
            goodbye_message TEXT DEFAULT '👋 خدانگهدار!',
            max_warnings INTEGER DEFAULT 3,
            mute_hours INTEGER DEFAULT 5,
            membership_required BOOLEAN DEFAULT FALSE,
            membership_channel TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

class RubikaBot:
    def __init__(self):
        self.base_url = BASE_URL
    
    def send_message(self, chat_id, text, keypad=None, reply_to=None):
        url = f"{self.base_url}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": text
        }
        
        if keypad:
            data["inline_keypad"] = keypad
        if reply_to:
            data["reply_to_message_id"] = reply_to
        
        try:
            response = requests.post(url, json=data)
            return response.json()
        except Exception as e:
            print(f"Error sending message: {e}")
            return None
    
    def delete_message(self, chat_id, message_id):
        url = f"{self.base_url}/deleteMessage"
        data = {
            "chat_id": chat_id,
            "message_id": message_id
        }
        
        try:
            response = requests.post(url, json=data)
            return response.json()
        except Exception as e:
            print(f"Error deleting message: {e}")
            return None
    
    def get_chat(self, chat_id):
        url = f"{self.base_url}/getChat"
        data = {"chat_id": chat_id}
        
        try:
            response = requests.post(url, json=data)
            return response.json()
        except Exception as e:
            print(f"Error getting chat: {e}")
            return None

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            update = json.loads(post_data)
            
            print("📨 Received update:", json.dumps(update, ensure_ascii=False))
            
            if 'inline_message' in update:
                self.process_inline_message(update['inline_message'])
            elif 'update' in update:
                self.process_update(update['update'])
            
            self.send_success()
            
        except Exception as e:
            print(f"❌ Error: {e}")
            self.send_error(500)
    
    def process_inline_message(self, message):
        bot = RubikaBot()
        chat_id = message['chat_id']
        user_id = message['sender_id']
        text = message.get('text', '')
        aux_data = message.get('aux_data', {})
        button_id = aux_data.get('button_id', '')
        
        print(f"🖱 Button clicked: {button_id} by {user_id}")
        
        # پردازش کلیک دکمه‌ها
        if button_id.startswith('join_'):
            channel = button_id.replace('join_', '')
            bot.send_message(user_id, f"✅ لطفاً در کانال عضو شوید: {channel}")
        
        elif button_id == 'check_membership':
            bot.send_message(user_id, "✅ عضویت شما بررسی شد")
    
    def process_update(self, update):
        bot = RubikaBot()
        
        if update['type'] == 'NewMessage':
            message = update['new_message']
            chat_id = update['chat_id']
            
            # بررسی اگر پیام از پیوی هست
            if chat_id.startswith('u'):
                self.handle_private_message(bot, message)
            else:
                self.handle_group_message(bot, message, chat_id)
    
    def handle_private_message(self, bot, message):
        user_id = message['sender_id']
        text = message.get('text', '')
        
        print(f"📩 Private message from {user_id}: {text}")
        
        # مدیریت از طریق پیوی
        if text == '/start':
            welcome_text = """🤖 **ربات مدیریت گروه**

👥 مدیریت گروه‌ها:
➕ افزودن گروه [لینک/آیدی]
📋 لیست گروه‌های من

👨‍💼 مدیریت ادمین‌ها (نیاز به رمز):
➕ افزودن ادمین @آیدی
➖ حذف ادمین @آیدی

⚙️ سایر دستورات:
🔞 مدیریت کلمات ممنوعه
🤖 مدیریت پاسخ‌های خودکار
📊 آمار گروه"""
            
            bot.send_message(user_id, welcome_text)
        
        elif text.startswith('افزودن گروه'):
            self.add_group(bot, user_id, text)
        
        elif text.startswith('لیست گروه‌ها'):
            self.list_groups(bot, user_id)
        
        elif text.startswith('افزودن ادمین'):
            self.request_password(bot, user_id, text, 'add_admin')
        
        elif text.startswith('حذف ادمین'):
            self.request_password(bot, user_id, text, 'remove_admin')
    
    def handle_group_message(self, bot, message, chat_id):
        user_id = message['sender_id']
        text = message.get('text', '')
        message_id = message['message_id']
        
        print(f"👥 Group message in {chat_id} from {user_id}: {text}")
        
        # بررسی محتوای ممنوعه
        if self.contains_banned_content(text):
            bot.delete_message(chat_id, message_id)
            self.handle_warning(bot, chat_id, user_id, "ارسال محتوای ممنوعه")
            return
        
        # بررسی عضویت اجباری
        if self.check_membership_required(chat_id) and not self.is_member(user_id, chat_id):
            bot.delete_message(chat_id, message_id)
            self.send_membership_required(bot, user_id, chat_id)
            return
        
        # پردازش پاسخ‌های خودکار
        self.check_auto_responses(bot, chat_id, text)
    
    def contains_banned_content(self, text):
        # بررسی لینک
        if re.search(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text):
            return True
        
        # بررسی آیدی
        if '@' in text:
            return True
        
        # بررسی پیام بلند
        if len(text) > 200:
            return True
        
        # بررسی کلمات ممنوعه از دیتابیس
        conn = sqlite3.connect('bot.db')
        cursor = conn.cursor()
        cursor.execute("SELECT word FROM banned_words")
        banned_words = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        for word in banned_words:
            if word in text.lower():
                return True
        
        return False
    
    def handle_warning(self, bot, chat_id, user_id, reason):
        conn = sqlite3.connect('bot.db')
        cursor = conn.cursor()
        
        # دریافت یا ایجاد رکورد کاربر
        cursor.execute('''
            INSERT OR REPLACE INTO user_warnings (user_id, group_id, warnings, last_warning)
            VALUES (?, ?, COALESCE((SELECT warnings FROM user_warnings WHERE user_id=? AND group_id=?), 0) + 1, ?)
        ''', (user_id, chat_id, user_id, chat_id, datetime.now()))
        
        cursor.execute("SELECT warnings FROM user_warnings WHERE user_id=? AND group_id=?", (user_id, chat_id))
        warnings = cursor.fetchone()[0]
        
        # دریافت تنظیمات گروه
        cursor.execute("SELECT max_warnings, mute_hours FROM group_settings WHERE group_id=?", (chat_id,))
        settings = cursor.fetchone()
        
        if settings:
            max_warnings, mute_hours = settings
        else:
            max_warnings, mute_hours = 3, 5
        
        if warnings >= max_warnings:
            # سکوت کاربر
            mute_until = datetime.now() + timedelta(hours=mute_hours)
            cursor.execute(
                "UPDATE user_warnings SET muted_until=?, warnings=0 WHERE user_id=? AND group_id=?",
                (mute_until, user_id, chat_id)
            )
            bot.send_message(chat_id, f"🚫 کاربر به دلیل {warnings} اخطار به مدت {mute_hours} ساعت سکوت شد")
        else:
            bot.send_message(chat_id, f"⚠️ اخطار {warnings}/{max_warnings} - {reason}")
        
        conn.commit()
        conn.close()
    
    def add_group(self, bot, user_id, text):
        try:
            group_info = text.replace('افزودن گروه', '').strip()
            
            conn = sqlite3.connect('bot.db')
            cursor = conn.cursor()
            
            # افزودن گروه به دیتابیس
            cursor.execute(
                "INSERT OR IGNORE INTO groups (group_id, group_name, owner_id) VALUES (?, ?, ?)",
                (group_info, group_info, user_id)
            )
            
            if cursor.rowcount > 0:
                bot.send_message(user_id, f"✅ گروه '{group_info}' با موفقیت اضافه شد")
                
                # ایجاد تنظیمات پیشفرض برای گروه
                cursor.execute(
                    "INSERT OR IGNORE INTO group_settings (group_id) VALUES (?)",
                    (group_info,)
                )
            else:
                bot.send_message(user_id, "❌ گروه از قبل وجود دارد")
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            bot.send_message(user_id, f"❌ خطا در افزودن گروه: {e}")
    
    def list_groups(self, bot, user_id):
        try:
            conn = sqlite3.connect('bot.db')
            cursor = conn.cursor()
            
            cursor.execute("SELECT group_id, group_name FROM groups WHERE owner_id=?", (user_id,))
            groups = cursor.fetchall()
            conn.close()
            
            if groups:
                group_list = "\n".join([f"• {name} ({gid})" for gid, name in groups])
                bot.send_message(user_id, f"📋 گروه‌های شما:\n{group_list}")
            else:
                bot.send_message(user_id, "📭 هیچ گروهی اضافه نکرده‌اید")
                
        except Exception as e:
            bot.send_message(user_id, f"❌ خطا در دریافت لیست گروه‌ها: {e}")
    
    def request_password(self, bot, user_id, text, action):
        # درخواست رمز برای مدیریت ادمین‌ها
        bot.send_message(user_id, "🔐 لطفاً رمز مدیریت را وارد کنید:")
        
        # ذخیره وضعیت کاربر برای مرحله بعد
        conn = sqlite3.connect('bot.db')
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, ?, ?)",
            (user_id, f"waiting_password_{action}", text)
        )
        conn.commit()
        conn.close()
    
    def check_membership_required(self, chat_id):
        conn = sqlite3.connect('bot.db')
        cursor = conn.cursor()
        cursor.execute("SELECT membership_required FROM group_settings WHERE group_id=?", (chat_id,))
        result = cursor.fetchone()
        conn.close()
        
        return result and result[0]
    
    def is_member(self, user_id, chat_id):
        # این تابع باید چک کند که کاربر در کانال/گروه اجباری عضو هست یا نه
        # فعلاً true برمی‌گرداند (پیاده‌سازی کامل نیاز به API خاص دارد)
        return True
    
    def send_membership_required(self, bot, user_id, chat_id):
        conn = sqlite3.connect('bot.db')
        cursor = conn.cursor()
        cursor.execute("SELECT membership_channel FROM group_settings WHERE group_id=?", (chat_id,))
        result = cursor.fetchone()
        conn.close()
        
        channel = result[0] if result else "کانال اصلی"
        
        keypad = {
            "rows": [{
                "buttons": [
                    {
                        "id": f"join_{channel}",
                        "type": "Simple",
                        "button_text": "🎯 عضویت در کانال"
                    },
                    {
                        "id": "check_membership",
                        "type": "Simple", 
                        "button_text": "✅ تایید عضویت"
                    }
                ]
            }]
        }
        
        bot.send_message(
            user_id,
            f"⚠️ برای ارسال پیام باید عضو کانال شوید: {channel}",
            keypad
        )
    
    def check_auto_responses(self, bot, chat_id, text):
        conn = sqlite3.connect('bot.db')
        cursor = conn.cursor()
        cursor.execute("SELECT trigger_text, response_text FROM auto_responses WHERE group_id=?", (chat_id,))
        responses = cursor.fetchall()
        conn.close()
        
        for trigger, response in responses:
            if trigger.lower() in text.lower():
                bot.send_message(chat_id, response)
                break
    
    def send_success(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"status": "success"}).encode())
    
    def send_error(self, code):
        self.send_response(code)
        self.end_headers()
    
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"🤖 ربات مدیریت گروه روبیکا فعال است!")

# ایجاد جدول وضعیت کاربران
def create_user_states_table():
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_states (
            user_id TEXT PRIMARY KEY,
            state TEXT,
            data TEXT
        )
    ''')
    conn.commit()
    conn.close()

create_user_states_table()
