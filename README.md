# 🏆 Discord Lomba & Hackathon Notifier Bot

Bot Discord otomatis yang memantau postingan Instagram tentang **lomba, hackathon, kompetisi coding, UI/UX, data science, dll.** dan mengirimkan notifikasi embed lengkap dengan mention role ke server Discord kamu.

---

## 🌟 Fitur Utama

- 📢 **Auto Ping Server**: Otomatis mention role (misal `@Lomba Hunters`, `@everyone`, atau `@here`) saat ada lomba baru.
- 🎨 **Rich Discord Embed**: Menampilkan judul, preview caption, akun pembuat, gambar poster, dan tautan langsung ke Instagram.
- 🎯 **Filter Keyword Cerdas**: Hanya mem-ping postingan yang mengandung kata kunci lomba/hackathon (seperti *hackathon*, *coding*, *lomba*, *ui/ux*, *datathon*, *total hadiah*).
- 🛡️ **Deduplikasi dengan SQLite**: Mencegah spam. Setiap postingan yang sudah pernah dikirim tidak akan dikirim ulang.
- ⚡ **Slash Commands Modern**:
  - `/ping_test`: Tes notifikasi embed dan izin ping bot di channel kamu.
  - `/check_lomba`: Cek postingan baru secara manual kapan saja.
  - `/status`: Cek status bot, jumlah lomba yang tersimpan, dan akun yang dipantau.
  - `/recent_lomba`: Menampilkan 5 info lomba terakhir yang tersimpan di database.
- 🔄 **Dukungan Berbagai Mode Instagram**:
  - **RSS / RSSHub** (Sangat disarankan & anti-blokir).
  - **Instaloader** (Direct scraping publik atau dengan login).
  - **Mock / Demo Mode** (Untuk uji coba langsung tanpa perlu koneksi Instagram).

---

## 🚀 Panduan Instalasi Cepat

### 1. Buka Direktori Bot
```bash
cd "K:\12. Code Projects\discord-lomba-bot"
```

### 2. Buat Virtual Environment & Install Dependensi
```bash
python -m venv venv
# Di Windows:
.\venv\Scripts\activate
# Install library yang dibutuhkan:
pip install -r requirements.txt
```

---

## 🔑 Langkah Pembuatan Bot Discord

1. Buka [Discord Developer Portal](https://discord.com/developers/applications).
2. Klik tombol **New Application**, beri nama (misal `Lomba Radar`).
3. Masuk ke tab **Bot** di menu sebelah kiri:
   - Klik **Reset Token** untuk menyalin token bot kamu.
   - Scroll ke bawah ke bagian **Privileged Gateway Intents** dan aktifkan:
     - `Message Content Intent`
     - `Server Members Intent`
4. Masuk ke tab **OAuth2** -> **URL Generator**:
   - Di bagian **Scopes**, centang:
     - `bot`
     - `applications.commands`
   - Di bagian **Bot Permissions**, centang:
     - `Send Messages`
     - `Embed Links`
     - `Mention Everyone` (untuk mengizinkan bot me-mention role)
     - `Read Message History`
     - `Use External Emojis`
5. Salin URL di bagian bawah dan buka di browser untuk mengundang bot ke server Discord kamu.

---

## ⚙️ Konfigurasi `.env`

Salin file `.env.example` menjadi `.env`:
```bash
copy .env.example .env
```

Buka file `.env` dan sesuaikan nilainya:

```env
# Token bot dari Discord Developer Portal
DISCORD_TOKEN=MTE5OTxxxxxxxxxxxxxxx

# ID Channel Discord tempat info lomba dikirim
# (Cara ambil: Aktifkan Developer Mode di Discord -> Klik kanan channel -> Copy Channel ID)
DISCORD_CHANNEL_ID=123456789012345678

# Role yang ingin dimention:
# - Masukkan ID Role (contoh: 987654321098765432)
# - Atau tulis "everyone" untuk @everyone
# - Atau tulis "here" untuk @here
# - Atau kosongkan jika tidak ingin mention
DISCORD_PING_ROLE_ID=everyone

# Frekuensi pengecekan postingan baru (dalam menit)
CHECK_INTERVAL_MINUTES=30

# Akun Instagram yang dipantau (pisahkan dengan koma, tanpa @)
TARGET_ACCOUNTS=hackathon_id,infolomba,lombanasional,eventkampus,dicoding

# Cek lomba dengan mock data terlebih dahulu (true/false)
ENABLE_MOCK_DATA=false
```

---

## 📸 Strategi Pemantauan Instagram

Instagram memiliki sistem proteksi ketat (login wall & rate limiting). Kamu memiliki 3 opsi:

### Opsi A: RSS / RSSHub (Paling Direkomendasikan & Stabil ⭐)
Gunakan RSS bridge seperti RSSHub atau [RSS.app](https://rss.app).
Contoh jika menggunakan RSSHub publik/self-hosted:
```env
RSS_FEED_TEMPLATE=https://rsshub.app/instagram/user/{username}
```
Metode ini tidak memerlukan login IG dan tidak akan terkena checkpoint/banned.

### Opsi B: Instaloader Langsung
Secara default, bot menggunakan library `instaloader`. Jika Instagram meminta login, kamu bisa mengisi `IG_USERNAME` dan `IG_PASSWORD` akun kedua (burner account) di file `.env`.

### Opsi C: Mode Mock / Demo
Untuk memastikan bot Discord berfungsi dengan baik sebelum menyambungkan Instagram asli, aktifkan:
```env
ENABLE_MOCK_DATA=true
```
Bot akan memuat postingan hackathon contoh, mengirimkannya ke Discord dengan embed rapi dan mention role, serta mencatatnya ke database SQLite.

---

## 🏃 Menjalankan Bot

Jalankan perintah berikut:
```bash
python bot.py
```

Setelah bot online:
1. Ketik `/ping_test` di Discord untuk memverifikasi izin bot di channel target.
2. Bot akan otomatis memeriksa akun Instagram target setiap 30 menit (atau sesuai `CHECK_INTERVAL_MINUTES`).
3. Kamu juga bisa menjalankan perintah `/check_lomba` kapan saja untuk memeriksa secara langsung.

