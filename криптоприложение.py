import tkinter as tk
from tkinter import messagebox
import requests
import threading
import time
from datetime import datetime

CRYPTOCURRENCIES = [
    "bitcoin", "ethereum", "tether", "binancecoin", "solana",
    "ripple", "dogecoin", "cardano", "avalanche-2", "tron"
]

def get_crypto_data():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "ids": ",".join(CRYPTOCURRENCIES),
        "order": "market_cap_desc",
        "per_page": 10,
        "page": 1,
        "sparkline": False
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        return response.json()
    except Exception as e:
        return []

def make_comment(change):
    if change is None:
        return "Нет данных."
    if change > 5:
        return "📈 Сильный рост. Присмотрись к покупке."
    elif change > 0:
        return "🟢 Умеренный рост. Можно наблюдать."
    elif change > -5:
        return "🟡 Небольшое падение. Потерпи."
    else:
        return "🔻 Сильное падение. Возможность купить подешевле."

def show_crypto_report(output_text, show_popups=True):
    crypto_data = get_crypto_data()
    if not crypto_data:
        output_text.insert(tk.END, "❌ Не удалось получить данные\n")
        return

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    output_text.insert(tk.END, f"\nОбновление: {now}\n")
    output_text.insert(tk.END, "-"*40 + "\n")

    for coin in crypto_data:
        name = coin["name"]
        price = coin["current_price"]
        change = coin["price_change_percentage_24h"]
        comment = make_comment(change)
        line = f"{name}: ${price:.2f} ({change:+.2f}%)\n{comment}\n\n"
        output_text.insert(tk.END, line)
        if show_popups:
            messagebox.showinfo(f"{name} 📊", f"{name}: ${price:.2f} ({change:+.2f}%)\n{comment}")

def start_auto_update(interval_min, output_text):
    def update_loop():
        while True:
            show_crypto_report(output_text, show_popups=False)
            time.sleep(interval_min * 60)
    t = threading.Thread(target=update_loop, daemon=True)
    t.start()

# === Графическое окно ===
root = tk.Tk()
root.title("CryptoBot Уведомления")
root.geometry("600x500")

frame = tk.Frame(root)
frame.pack(pady=10)

output_text = tk.Text(frame, height=25, width=70)
output_text.pack()

btn_frame = tk.Frame(root)
btn_frame.pack(pady=10)

tk.Button(btn_frame, text="📥 Получить курсы", command=lambda: show_crypto_report(output_text)).grid(row=0, column=0, padx=5)

def start_auto():
    try:
        mins = int(auto_entry.get())
        start_auto_update(mins, output_text)
        messagebox.showinfo("✅", f"Автообновление каждые {mins} мин включено.")
    except:
        messagebox.showerror("Ошибка", "Введите число минут.")

tk.Label(btn_frame, text="Автообновление (мин):").grid(row=0, column=1, padx=5)
auto_entry = tk.Entry(btn_frame, width=5)
auto_entry.insert(0, "10")
auto_entry.grid(row=0, column=2, padx=5)
tk.Button(btn_frame, text="▶️ Запуск", command=start_auto).grid(row=0, column=3, padx=5)

root.mainloop()
