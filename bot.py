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
            "1. Silakan lakukan transfer ke QRIS berikut [https://photos.app.goo.gl/tJmideDj46swUsZdA]\n"
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
        # Payload data untuk Midtrans Core API (QRIS)
def buat_pesanan():
    nama = "User"
    payload = {  # <-- BENAR: Sejajar dengan baris nama (sama-sama 4 spasi dari def)
        "transaction_details": {
            "order_id": "ORDER-123",
            "gross_amount": 50000
        },


        "custom_field1": user_id # Menyimpan ID Telegram user agar terbaca saat callback sukses
    }
    
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Basic {MIDTRANS_SERVER_KEY}"
    }
    
    # Request ke Midtrans (Sekarang sejajar dengan headers)
    response = requests.post(MIDTRANS_API_URL, json=payload, headers=headers)

    data = response.json()
    
         if response.status_code == 201:
        # Kode Anda selanjutnya di sini (maju 4 spasi dari if)

            # Mengambil link QRIS dari response Midtrans
            actions = data.get('actions', [])
            qris_url = next((action['url'] for action in actions if action['name'] == 'generate-qr-code'), None)
            
         if qris_url:
                bot.send_message(
                    message.chat.id,
                    f"🧾 *Invoice Terbuat!*\n"
                    f"Order ID: `{order_id}`\n"
                    f"Total Bayar: *Rp {amount:,}*\n\n"
                    f"Silakan scan QRIS di bawah ini menggunakan GoPay, OVO, Dana, LinkAja, atau Mobile Banking Anda. "
                    f"Saldo akan masuk otomatis setelah pembayaran sukses.",
                    parse_mode="Markdown"
                )
                # Kirim gambar QRIS langsung ke user
                bot.send_photo(message.chat.id, qris_url)
        else:
                bot.reply_to(message, "❌ Gagal membuat QRIS. Silakan coba lagi nanti.")
        else:
            bot.reply_to(message, f"❌ Terjadi kesalahan sistem Payment Gateway: {data.get('status_message')}")
            
        except ValueError:
        bot.reply_to(message, "❌ Nominal harus berupa angka penuh tanpa titik/koma.")

# 3. ENDPOINT WEBHOOK / CALLBACK (Menerima Notifikasi dari Midtrans)
@app.route('/midtrans-callback', methods=['POST'])
def midtrans_callback():
    data = request.get_json()
    
    order_id = data.get('order_id')
    transaction_status = data.get('transaction_status')
    fraud_status = data.get('fraud_status')
    gross_amount = int(float(data.get('gross_amount', 0)))
    user_id = data.get('custom_field1') # ID Telegram yang kita titipkan tadi
    
    # Validasi Status Pembayaran Berhasil
    if transaction_status == 'settlement':
        if fraud_status == 'accept' or fraud_status is None:
            # Tambahkan saldo ke user di database Anda
            user_balances[user_id] = user_balances.get(user_id, 0) + gross_amount
            
            # Beri notifikasi langsung ke user via bot Telegram secara real-time
            success_msg = (
                f"🎉 *DEPOSIT BERHASIL!*\n\n"
                f"Dana sebesar *Rp {gross_amount:,}* telah ditambahkan ke akun Anda.\n"
                f"Terima kasih telah melakukan pembayaran."
            )
            bot.send_message(user_id, success_msg, parse_mode="Markdown")
            
    return jsonify({"status": "OK"}), 200

# 4. INTEGRASI ROUTE TELEGRAM WEBHOOK (Agar bot & flask berjalan di port yang sama)
@app.route('/' + API_TOKEN, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook()
    # Ganti URL_SERVER_ANDA dengan url dari Render/Heroku tempat Anda menaruh bot ini
    bot.set_webhook(url='https://www.pythonanywhere.com/user/polay90/webapps/#tab_id_polay90_pythonanywhere_com/' + API_TOKEN)
    return "Bot Webhook Berhasil Terpasang!", 200

if __name__ == "__main__":
    # Menjalankan server Flask (Port 5000)
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))

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

