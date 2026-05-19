import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# GANTI DENGAN TOKEN BOT TELEGRAM ANDA
API_TOKEN = '8993353829:AAFeDOCzz4hj7pGrdNScIpIYw4dGViEm7OM'
bot = telebot.TeleBot(API_TOKEN)

# Database sederhana di memori (Jika bot restart, saldo akan kembali ke 0)
# Untuk produksi, disarankan menggunakan database asli seperti SQLite atau PostgreSQL
user_balances = {}

# Daftar Menu, Harga, dan Deskripsi Input
MENU_DATA = {
    "lacak": {"nama": "Lacak Peserta Jamsostek", "harga": 100000, "input": "NIK peserta"},
    "simbo": {"nama": "Generate Simbo Kode Plus", "harga": 250000, "input": "simbol JHT (contoh: AG, BB, DF, KO, PT)"},
    "riset_akun": {"nama": "Riset Akun", "harga": 300000, "input": "KTP / KPJ / Nama Ibu Kandung"},
    "riset_kode": {"nama": "Riset Kode Numeric", "harga": 450000, "input": "Paklaring / KPJ"},
    "bongkar": {"nama": "Bongkar Akun", "harga": 10000, "input": "KPJ / NIK / Nama"},
    "ternak": {"nama": "Ternak Wilayah Request", "harga": 250000, "input": "11 digit Nomor KPJ random"},
}

def get_balance(user_id):
    return user_balances.get(user_id, 0)

def main_keyboard(user_id):
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    
    # Tombol Menu Layanan
    for key, val in MENU_DATA.items():
        markup.add(InlineKeyboardButton(f"🛠️ {val['nama']} — Rp {val['harga']:,}", callback_data=f"menu_{key}"))
        
    # Tombol Dompet / Deposit
    markup.add(
        InlineKeyboardButton(f"💳 Isi Saldo / Deposit", callback_data="deposit"),
        InlineKeyboardButton(f"💰 Cek Saldo (Rp {get_balance(user_id):,})", callback_data="cek_saldo")
    )
    return markup

# Command /start
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_id = message.from_user.id
    if user_id not in user_balances:
        user_balances[user_id] = 0 # Saldo awal 0
        
    welcome_text = (
        "👋 Selamat datang di Bot Layanan Jamsostek!\n\n"
        "Silakan pilih menu di bawah ini. Pastikan saldo Anda mencukupi "
        "sebelum melakukan eksekusi perintah."
    )
    bot.reply_to(message, welcome_text, reply_markup=main_keyboard(user_id))

# Callback Handler untuk Tombol
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id
    
    if call.data.startswith("menu_"):
        menu_key = call.data.split("_")[1]
        menu = MENU_DATA[menu_key]
        saldo_sekarang = get_balance(user_id)
        
        # Proteksi Saldo
        if saldo_sekarang < menu['harga']:
            bot.answer_callback_query(call.id, "❌ Saldo Anda tidak mencukupi!")
            bot.send_message(
                call.message.chat.id, 
                f"⚠️ Gagal mengakses *{menu['nama']}*.\n"
                f"Saldo Anda: Rp {saldo_sekarang:,}\n"
                f"Harga Layanan: Rp {menu['harga']:,}\n\n"
                f"Silakan lakukan deposit terlebih dahulu via QRIS.",
                parse_mode="Markdown"
            )
        else:
            bot.answer_callback_query(call.id)
            msg = bot.send_message(
                call.message.chat.id, 
                f"📝 *{menu['nama']}* (Rp {menu['harga']:,})\n"
                f"Silakan masukkan {menu['input']}:",
                parse_mode="Markdown"
            )
            # Lanjut ke proses penangkapan data input dari user
            bot.register_next_step_handler(msg, process_menu_input, menu_key, menu)
            
    elif call.data == "deposit":
        bot.answer_callback_query(call.id)
        # Skenario QRIS Statis / Instruksi Deposit
        deposit_text = (
            "🤖 *Menu Deposit / Pembayaran QRIS*\n\n"
            "1. Silakan lakukan transfer ke QRIS berikut [https://photos.app.goo.gl/6urEv3Q4MM6dZ4fFA]\n"
            "2. Kirimkan bukti transfer ke Admin (@play2026).\n"
            "3. Saldo akan ditambahkan manual oleh admin atau via sistem terintegrasi.\n\n"
            "_*Untuk simulasi trial/testing bot ini, ketik perintah `/topup 500000` untuk mengisi saldo instan._"
        )
        bot.send_message(call.message.chat.id, deposit_text, parse_mode="Markdown")
        
    elif call.data == "cek_saldo":
        bot.answer_callback_query(call.id, f"Saldo Anda: Rp {get_balance(user_id):,}", show_alert=True)

# Memproses Input Setelah Memilih Menu dan Saldo Cukup
def process_menu_input(message, menu_key, menu):
    user_id = message.from_user.id
    user_input = message.text
    
    # Validasi khusus untuk menu Ternak Wilayah (Harus 11 digit nomor)
    if menu_key == "ternak":
        if not user_input.isdigit() or len(user_input) != 11:
            msg = bot.reply_to(message, "❌ Input tidak valid! Nomor KPJ harus berupa *11 digit angka*. Silakan ulangi:")
            bot.register_next_step_handler(msg, process_menu_input, menu_key, menu)
            return

    # Potong Saldo User
    user_balances[user_id] -= menu['harga']
    saldo_sisa = user_balances[user_id]
    
    # Respon Sukses / Eksekusi data
    sukses_text = (
        f"✅ *Permintaan Berhasil Diterima!*\n\n"
        f" LAYANAN: {menu['nama']}\n"
        f" INPUT DATA: `{user_input}`\n"
        f"💸 BIAYA: Rp {menu['harga']:,}\n"
        f"💰 SISA SALDO: Rp {saldo_sisa:,}\n\n"
        f"Proses sedang dijalankan oleh sistem. Mohon tunggu informasi berikutnya."
    )
    bot.send_message(message.chat.id, sukses_text, parse_mode="Markdown", reply_markup=main_keyboard(user_id))

# FITUR TAMBAHAN: Perintah Rahasia untuk Simulasi Isi Saldo Mandiri
@bot.message_handler(commands=['topup'])
def simulasi_topup(message):
    user_id = message.from_user.id
    try:
        amount = int(message.text.split()[1])
        user_balances[user_id] = user_balances.get(user_id, 0) + amount
        bot.reply_to(message, f"💰 Berhasil simulasi deposit! Saldo Anda saat ini: *Rp {user_balances[user_id]:,}*", parse_mode="Markdown", reply_markup=main_keyboard(user_id))
    except:
        bot.reply_to(message, "Format salah. Gunakan contoh: `/topup 500000`")

# Menjalankan Bot
if __name__ == '__main__':
    print("Bot sedang berjalan...")
    bot.infinity_polling()

