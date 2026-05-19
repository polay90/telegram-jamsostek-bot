import os
import requests
from flask import Flask, request, jsonify
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# 配置 Config
API_TOKEN = '8993353829:AAFeDOCzz4hj7pGrdNScIpIYw4dGViEm7OM'
MIDTRANS_SERVER_KEY = 'Mid-server-KXYFhEy33owLMSDacfH22hDU' # Dapatkan di dashboard Midtrans (Sandbox/Production)
MIDTRANS_API_URL = 'https://api.sandbox.midtrans.com/v2/charge' # Gunakan api.midtrans.com jika sudah live

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# Simulasi Database Saldo
user_balances = {}

# 1. HANDLE TOMBOL DEPOSIT DI TELEGRAM
@bot.callback_query_handler(func=lambda call: call.data == "deposit")
def request_deposit_amount(call):
    msg = bot.send_message(call.message.chat.id, "💰 Masukkan nominal deposit (Contoh: 100000):")
    bot.register_next_step_handler(msg, generate_qris_payment)

# 2. MEMINTA QRIS KE MIDTRANS
def generate_qris_payment(message):
    user_id = str(message.from_user.id)
    try:
        amount = int(message.text)
        if amount < 10000:
            bot.reply_to(message, "❌ Minimal deposit adalah Rp 10.000.")
            return
            
        # Membuat Order ID unik untuk Midtrans (Contoh: DEP-USERID-TIMESTAMP)
        import time
        order_id = f"DEP-{user_id}-{int(time.time())}"
        
        # Payload data untuk Midtrans Core API (QRIS)
        payload = {
            "payment_type": "gopay", # gopay otomatis menghasilkan QRIS yang bisa di-scan semua e-wallet/m-banking
            "transaction_details": {
                "order_id": order_id,
                "gross_amount": amount
            },
            "custom_field1": user_id # Menyimpan ID Telegram user agar terbaca saat callback sukses
        }
        
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"Basic {MIDTRANS_SERVER_KEY}" # Server key biasanya di-encode base64, atau library midtrans-python menangani ini secara otomatis
        }
        
        # Request ke Midtrans
        # Catatan: Untuk kemudahan, disarankan menggunakan library resmi `midtransclient` bawaan Midtrans.
        # Ini adalah simulasi request dasar via HTTP POST:
        response = requests.post(MIDTRANS_API_URL, json=payload, auth=(MIDTRANS_SERVER_KEY, ''))
        data = response.json()
        
        if response.status_code == 201:
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
    bot.set_webhook(url='https://URL_SERVER_ANDA.com/' + API_TOKEN)
    return "Bot Webhook Berhasil Terpasang!", 200

if __name__ == "__main__":
    # Menjalankan server Flask (Port 5000)
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
