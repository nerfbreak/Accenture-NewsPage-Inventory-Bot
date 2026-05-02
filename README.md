# 🤖 Inventory Stock Adjustment Auto-Bot v1.0
**Created by: Rizki Firdaus**

Aplikasi automasi berbasis Python yang dirancang untuk mempercepat proses input data inventaris pada sistem Accenture NewsPage R5Office. Robot ini menangani tugas repetitif input SKU dan Quantity dari file CSV dengan presisi tinggi dan penanganan error yang cerdas.

## ✨ Fitur Utama
- **Smart-Wait Logic**: Menyesuaikan kecepatan input dengan beban loading server ASP.NET secara otomatis.
- **Bypass Error Popup**: Mendeteksi dan menangani popup peringatan (seperti "Cost Price Zero") secara mandiri.
- **Excel-to-CSV Integration**: Dilengkapi dengan file Excel Macro (.xlsm) untuk input data massal yang langsung terkonversi ke format robot.
- **Minimalist Console Interface**: Tampilan terminal yang bersih dan informatif untuk memantau proses secara real-time.
- **Safe Login**: Memberikan kendali penuh kepada pengguna untuk login secara manual sebelum automasi dimulai.

## 🛠️ Teknologi yang Digunakan
- **Python**: Bahasa pemrograman utama.
- **Playwright**: Framework automasi web untuk interaksi browser yang cepat dan andal.
- **Excel VBA (Macro)**: Untuk mempermudah persiapan data pengguna.
- **PyInstaller**: Untuk membungkus skrip menjadi aplikasi desktop (.exe).

## 🚀 Cara Penggunaan
1. Masukkan data SKU dan QTY pada file `Master_Input_Inventory.xlsm`.
2. Klik tombol **"GENERATE CSV & UPDATE"** pada Excel.
3. Jalankan `robot_inventory.exe`.
4. Login ke portal Accenture saat browser terbuka.
5. Tekan tombol Enter di terminal untuk memulai automasi.

---
*Project ini dikembangkan untuk tujuan efisiensi kerja tim internal dan optimasi manajemen inventaris.*
