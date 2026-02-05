import threading
import time
from datetime import datetime
import pandas as pd
import requests
import schedule
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from telegram import Bot
from tkinter import ttk, messagebox

vs_currency = 'usd'
cryptos = [
    'bitcoin', 'ethereum', 'tether', 'binancecoin', 'solana', 'ripple', 'dogecoin',
    'cardano', 'avalanche-2', 'tron', 'polkadot', 'chainlink', 'stellar', 'uniswap',
    'vechain', 'crypto-com-chain', 'leo-token', 'monero', 'eos', 'filecoin'
]
interval = 60
notify_on = 'all'

bot = Bot(token='8105231857:AAG6IRQocF2eWX4Zo7Byt-8EVm0azpfeVXc')
chat_id = '1237616867'

def get_crypto_data():
    url = 'https://api.coingecko.com/api/v3/coins/markets'
    params = {
        'vs_currency': vs_currency,
        'ids': ','.join(cryptos),
        'order': 'market_cap_desc',
        'per_page': len(cryptos),
        'page': 1,
        'sparkline': False
    }
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    return pd.DataFrame(r.json())

def compute_indicators(df):
    df['SMA7'] = df['current_price'].rolling(window=7, min_periods=1).mean()
    df['EMA7'] = df['current_price'].ewm(span=7, adjust=False).mean()
    delta = df['current_price'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI14'] = 100 - (100 / (1 + rs))
    exp1 = df['current_price'].ewm(span=12, adjust=False).mean()
    exp2 = df['current_price'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['MACD_signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    return df

def analyze(df):
    advice = {}
    for _, row in df.iterrows():
        change = row['price_change_percentage_24h'] or 0
        rsi = row['RSI14'] or 0
        if change > 2 and rsi < 70:
            advice[row['id']] = 'BUY'
        elif change < -2 and rsi > 30:
            advice[row['id']] = 'BUY'
        else:
            advice[row['id']] = 'HOLD'
    return advice

def send_telegram(text):
    try:
        bot.send_message(chat_id=chat_id, text=text, parse_mode='HTML')
    except Exception as e:
        print(f"Ошибка отправки в Telegram: {e}")

class CryptoApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('CryptoBot')
        self.geometry('1000x700')
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        cols = ('symbol', 'price', 'change', 'action')
        self.tree = ttk.Treeview(self, columns=cols, show='headings')
        for c in cols:
            self.tree.heading(c, text=c)
        self.tree.pack(fill=tk.BOTH, expand=True)

        frm = tk.Frame(self)
        frm.pack(pady=5)
        tk.Button(frm, text='Обновить', command=self.refresh).pack(side=tk.LEFT, padx=5)
        tk.Button(frm, text='Графики', command=self.show_charts).pack(side=tk.LEFT)
        tk.Label(frm, text='Интервал, мин:').pack(side=tk.LEFT, padx=5)
        self.ent = tk.Entry(frm, width=5)
        self.ent.insert(0, str(interval))
        self.ent.pack(side=tk.LEFT)
        tk.Button(frm, text='Старт авто', command=self.start_auto).pack(side=tk.LEFT, padx=5)

    def refresh(self):
        df = get_crypto_data()
        if df.empty:
            messagebox.showerror('Ошибка', 'Нет данных')
            return
        df = compute_indicators(df)
        adv = analyze(df)
        for i in self.tree.get_children():
            self.tree.delete(i)
        for _, r in df.iterrows():
            self.tree.insert('', 'end', values=(
                r['symbol'].upper(),
                f'${r["current_price"]:.2f}',
                f'{r["price_change_percentage_24h"]:.2f}%',
                adv[r['id']]
            ))
        msg = '<b>Криптоотчёт</b>\n'
        for _, r in df.iterrows():
            msg += f'{r["symbol"].upper()}: ${r["current_price"]:.2f} ({r["price_change_percentage_24h"]:.2f}%) {adv[r["id"]]}\n'
        if notify_on == 'all':
            send_telegram(msg)

    def show_charts(self):
        df = get_crypto_data()
        if df.empty:
            messagebox.showerror('Ошибка', 'Нет данных для графиков')
            return
        for cid in df['id'][:5]:
            prices = [df.loc[df['id'] == cid, 'current_price'].values[0]] * 3
            fig, ax = plt.subplots()
            ax.plot([1, 7, 30], prices)
            ax.set_title(cid)
            canvas = FigureCanvasTkAgg(fig, self)
            canvas.get_tk_widget().pack()
            canvas.draw()

    def start_auto(self):
        mins = int(self.ent.get())
        schedule.every(mins).minutes.do(self.refresh)
        threading.Thread(target=self._run_scheduler, daemon=True).start()

    @staticmethod
    def _run_scheduler():
        while True:
            schedule.run_pending()
            time.sleep(1)

if __name__ == '__main__':
    CryptoApp().mainloop()
