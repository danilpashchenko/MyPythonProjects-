import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk, filedialog
import threading
import queue
import time
import socket
import random
import os
import json
import math
from datetime import datetime
from collections import defaultdict, deque

# Попытка импорта requests для GeoIP
try:
    import requests
except ImportError:
    requests = None

# Настройка логирования Scapy, чтобы не спамил в консоль
import logging

logging.getLogger("scapy.runtime").setLevel(logging.ERROR)

from scapy.all import (
    sniff, IP, TCP, UDP, ARP, Ether, send, srp, conf, wrpcap,
    DNS, DNSQR, DNSRR, getmacbyip, hexdump
)

# --- КОНСТАНТЫ ---
MAX_CAPTURED_PACKETS = 500
MAX_CONSOLE_LINES = 800
ANALYTICS_REFRESH_MS = 2000
BANDWIDTH_WINDOW_SEC = 10

# --- ГЛОБАЛЬНЫЕ НАСТРОЙКИ ---
conf.verb = 0
conf.use_pcap = True


def _detect_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '192.168.1.100'


def _detect_gateway(local_ip):
    parts = local_ip.rsplit('.', 1)
    if len(parts) == 2:
        return parts[0] + '.1'
    return '192.168.1.1'


_LOCAL_IP = _detect_local_ip()
_GATEWAY_IP = _detect_gateway(_LOCAL_IP)

class PashchenkoCyberSuite:
    def __init__(self, root):
        self.root = root
        self.root.title("PASHCHENKO CYBER SUITE v7.0 [ULTIMATE]")
        self.root.geometry("1400x950")
        self.root.configure(bg="#000000")

        # Очередь для потокобезопасного общения
        self.gui_queue = queue.Queue()

        # Состояние
        self.is_sniffing = False
        self.is_flooding = False
        self.captured_packets = deque(maxlen=MAX_CAPTURED_PACKETS)
        self.network_nodes = []
        self.analytics_lock = threading.Lock()
        self.analytics = self._new_analytics_state()
        self._analytics_refresh_id = None
        self._sniff_start_time = None

        # Стили
        self.setup_styles()

        # Запуск Интро
        self.show_intro()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TNotebook", background="#000000", borderwidth=0)
        style.configure("TNotebook.Tab", background="#111", foreground="#00FF00",
                        font=("Consolas", 11, "bold"), padding=[15, 8])
        style.map("TNotebook.Tab", background=[("selected", "#00FF00")],
                  foreground=[("selected", "black")])
        style.configure("TProgressbar", thickness=10, background="#00FF00", troughcolor="#111")

    # --- 0. КИНЕМАТОГРАФИЧНОЕ ИНТРО ---
    def show_intro(self):
        self.intro_frame = tk.Frame(self.root, bg="black")
        self.intro_frame.place(relx=0, rely=0, relwidth=1, relheight=1)

        # Матричный дождь (упрощенный)
        self.canvas_intro = tk.Canvas(self.intro_frame, bg="black", highlightthickness=0)
        self.canvas_intro.pack(fill=tk.BOTH, expand=True)

        # Текст по центру
        self.intro_text_id = self.canvas_intro.create_text(
            self.root.winfo_screenwidth() // 2, 300,
            text="", font=("Courier New", 40, "bold"), fill="#00FF00"
        )

        # Дисклеймер
        disclaimer = ("WARNING: This software is for EDUCATIONAL PURPOSES and AUTHORIZED PEN-TESTING only.\n"
                      "The author (Pashchenko) assumes no liability for misuse.\n"
                      "Initializing Kernel Modules...")

        self.disclaimer_id = self.canvas_intro.create_text(
            self.root.winfo_screenwidth() // 2, 500,
            text="", font=("Consolas", 12), fill="#008800"
        )

        # Анимация набора текста
        self.type_writer("MADE BY PASHCHENKO", self.intro_text_id, 0, 50,
                         lambda: self.type_writer(disclaimer, self.disclaimer_id, 0, 20, self.finish_intro))

    def type_writer(self, text, item_id, index, speed, callback=None):
        if index <= len(text):
            current_text = text[:index] + "█"  # Курсор
            self.canvas_intro.itemconfigure(item_id, text=current_text)
            self.root.after(speed, self.type_writer, text, item_id, index + 1, speed, callback)
        else:
            self.canvas_intro.itemconfigure(item_id, text=text)  # Убираем курсор
            if callback:
                self.root.after(1000, callback)

    def finish_intro(self):
        # Эффект растворения
        self.intro_frame.destroy()
        self.init_main_ui()

    # --- ГЛАВНЫЙ ИНТЕРФЕЙС ---
    def init_main_ui(self):
        # Верхняя панель
        header = tk.Frame(self.root, bg="#050505", height=50)
        header.pack(fill=tk.X)
        tk.Label(header, text="SYSTEM ONLINE | ROOT ACCESS GRANTED", fg="#00FF00", bg="#050505",
                 font=("Consolas", 10)).pack(side=tk.RIGHT, padx=20)
        tk.Label(header, text="PASHCHENKO SUITE v7.0", fg="#00FF00", bg="#050505", font=("Impact", 20)).pack(
            side=tk.LEFT, padx=20)

        # Табы (Notebook)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Создание вкладок
        self.tab_dashboard = tk.Frame(self.notebook, bg="black")
        self.tab_map = tk.Frame(self.notebook, bg="black")  # Feature 1
        self.tab_attack = tk.Frame(self.notebook, bg="black")  # Feature 2
        self.tab_inspector = tk.Frame(self.notebook, bg="black")  # Feature 4

        self.notebook.add(self.tab_dashboard, text=" [ DASHBOARD ] ")
        self.notebook.add(self.tab_map, text=" [ NET VISUALIZER ] ")
        self.notebook.add(self.tab_attack, text=" [ STRESS TEST ] ")
        self.notebook.add(self.tab_inspector, text=" [ PACKET INSPECTOR ] ")

        self.setup_dashboard()
        self.setup_visualizer()
        self.setup_attack_module()
        self.setup_inspector()

        # Запуск обработчика очереди GUI
        self.process_queue()

        # Запуск авто-обновления аналитики
        self._schedule_analytics_refresh()

    # --- ТАБ 1: DASHBOARD ---
    def setup_dashboard(self):
        # Сетка
        left_panel = tk.Frame(self.tab_dashboard, bg="#111", width=300)
        left_panel.pack(side=tk.LEFT, fill=tk.Y)

        right_panel = tk.Frame(self.tab_dashboard, bg="black")
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Контролы
        tk.Label(left_panel, text="TARGET SETTINGS", fg="white", bg="#111", font=("Consolas", 12, "bold")).pack(pady=10)
        self.entry_ip = self.create_input(left_panel, "TARGET IP:", _LOCAL_IP)
        self.entry_router_ip = self.create_input(left_panel, "ROUTER IP:", _GATEWAY_IP)

        # Кнопки действий
        self.btn_sniff = tk.Button(left_panel, text="START SNIFFER", bg="#003300", fg="lime",
                                   command=self.toggle_sniffer, font=("Consolas", 10, "bold"), relief=tk.FLAT)
        self.btn_sniff.pack(fill=tk.X, padx=10, pady=5)

        tk.Button(left_panel, text="RESET ANALYTICS", bg="#332200", fg="#ffcc66",
                  command=self.reset_analytics, font=("Consolas", 10)).pack(fill=tk.X, padx=10, pady=5)

        tk.Button(left_panel, text="GEOIP LOOKUP", bg="#001133", fg="cyan",
                  command=self.run_geoip, font=("Consolas", 10)).pack(fill=tk.X, padx=10, pady=5)

        tk.Button(left_panel, text="GENERATE HTML REPORT", bg="#331100", fg="orange",
                  command=self.generate_report, font=("Consolas", 10)).pack(fill=tk.X, padx=10, pady=5)

        # Live analytics panel (сверху — важнее)
        self.analytics_view = scrolledtext.ScrolledText(
            right_panel,
            height=14,
            bg="#080808",
            fg="#88ff88",
            font=("Consolas", 10),
            insertbackground="white"
        )
        self.analytics_view.pack(fill=tk.X, padx=5, pady=5)
        self.analytics_view.insert(
            tk.END,
            "=== TRAFFIC ANALYTICS ===\n"
            "Start sniffer to begin collecting data.\n"
            "Filters: TARGET IP + ROUTER IP.\n"
        )
        self.analytics_view.config(state=tk.DISABLED)

        # Лог (Терминал)
        self.console = scrolledtext.ScrolledText(right_panel, bg="black", fg="#00FF00", font=("Consolas", 10),
                                                 insertbackground="white")
        self.console.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))
        self.console.tag_config("ALERT", foreground="red", background="#220000")
        self.console.tag_config("INFO", foreground="cyan")
        self.console.tag_config("DATA", foreground="#FFFF00")

    # --- ТАБ 2: NETWORK VISUALIZER (НОВОВВЕДЕНИЕ 1) ---
    def setup_visualizer(self):
        control_frame = tk.Frame(self.tab_map, bg="#111")
        control_frame.pack(fill=tk.X)
        tk.Button(control_frame, text="SCAN & MAP NETWORK", bg="#004400", fg="white", command=self.run_map_scan).pack(
            pady=5)

        self.map_canvas = tk.Canvas(self.tab_map, bg="#050505", highlightthickness=0)
        self.map_canvas.pack(fill=tk.BOTH, expand=True)
        # Легенда
        self.map_canvas.create_text(100, 20, text="ROUTER (GATEWAY)", fill="red", font=("Consolas", 10))
        self.map_canvas.create_text(100, 40, text="DEVICE (NODE)", fill="#00FF00", font=("Consolas", 10))

    def run_map_scan(self):
        self.log("Starting ARP Scan for Map...", "INFO")
        threading.Thread(target=self._scan_thread, daemon=True).start()

    def _scan_thread(self):
        try:
            router_ip = self.entry_router_ip.get().strip()
            parts = router_ip.rsplit('.', 1)
            gw = f"{parts[0]}.0/24" if len(parts) == 2 else "192.168.1.0/24"
            self.gui_queue.put(("LOG", (f"Scanning subnet: {gw}", "INFO")))
            ans, _ = srp(Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=gw), timeout=2, verbose=False)
            nodes = []
            for _, rcv in ans:
                nodes.append({"ip": rcv.psrc, "mac": rcv.hwsrc})

            self.gui_queue.put(("DRAW_MAP", nodes))
        except Exception as e:
            self.gui_queue.put(("LOG", (f"Scan Error: {e}", "ALERT")))

    def draw_network_map(self, nodes):
        self.map_canvas.delete("node")
        w = self.map_canvas.winfo_width()
        h = self.map_canvas.winfo_height()
        cx, cy = w / 2, h / 2

        # Рисуем роутер
        self.map_canvas.create_oval(cx - 20, cy - 20, cx + 20, cy + 20, fill="red", outline="white", width=2,
                                    tags="node")
        self.map_canvas.create_text(cx, cy + 35, text="GATEWAY", fill="white", font=("Consolas", 8), tags="node")

        # Рисуем узлы по кругу
        count = len(nodes)
        if count == 0: return
        radius = min(w, h) / 3
        angle_step = 360 / count

        for i, node in enumerate(nodes):
            angle = math.radians(i * angle_step)
            nx = cx + radius * math.cos(angle)
            ny = cy + radius * math.sin(angle)

            # Линия связи
            self.map_canvas.create_line(cx, cy, nx, ny, fill="#333", dash=(2, 2), tags="node")
            # Узел
            self.map_canvas.create_oval(nx - 15, ny - 15, nx + 15, ny + 15, fill="#00FF00", outline="black",
                                        tags="node")
            self.map_canvas.create_text(nx, ny + 25, text=node['ip'], fill="#00FF00", font=("Consolas", 9), tags="node")
            self.map_canvas.create_text(nx, ny + 38, text=node['mac'], fill="#666", font=("Consolas", 7), tags="node")

    # --- ТАБ 3: STRESS TEST (НОВОВВЕДЕНИЕ 2) ---
    def setup_attack_module(self):
        frame = tk.Frame(self.tab_attack, bg="black")
        frame.pack(expand=True)

        tk.Label(frame, text="⚠ DANGER ZONE ⚠", fg="red", bg="black", font=("Impact", 30)).pack(pady=20)
        tk.Label(frame, text="TCP SYN FLOOD SIMULATOR", fg="white", bg="black", font=("Consolas", 14)).pack()

        self.flood_btn = tk.Button(frame, text="INITIATE FLOOD", bg="red", fg="white", font=("Consolas", 14, "bold"),
                                   command=self.toggle_flood, width=20, height=2)
        self.flood_btn.pack(pady=30)

        tk.Label(frame, text="* Only use on networks you own!", fg="#444", bg="black").pack()

    def toggle_flood(self):
        if not self.is_flooding:
            self.is_flooding = True
            self.flood_btn.config(text="STOP FLOOD", bg="white", fg="red")
            target = self.entry_ip.get()
            self.log(f"Starting Stress Test on {target}...", "ALERT")
            threading.Thread(target=self._flood_thread, args=(target,), daemon=True).start()
        else:
            self.is_flooding = False
            self.flood_btn.config(text="INITIATE FLOOD", bg="red", fg="white")
            self.log("Stress Test Stopped.", "INFO")

    def _flood_thread(self, target_ip):
        # Оптимизация: Предварительное создание пакета
        packet = IP(dst=target_ip) / TCP(dport=80, flags="S")
        try:
            while self.is_flooding:
                send(packet, verbose=0)
                # Имитация нагрузки, но с задержкой, чтобы не положить свой же интерфейс
                time.sleep(0.01)
        except Exception as e:
            self.gui_queue.put(("LOG", (f"Flood Error: {e}", "ALERT")))

    # --- ТАБ 4: PACKET INSPECTOR (НОВОВВЕДЕНИЕ 4) ---
    def setup_inspector(self):
        self.hex_view = scrolledtext.ScrolledText(self.tab_inspector, bg="#050505", fg="#00FF00", font=("Courier", 10))
        self.hex_view.pack(fill=tk.BOTH, expand=True)
        tk.Button(self.tab_inspector, text="REFRESH HEX DUMP (LAST PACKET)", command=self.show_last_packet_hex,
                  bg="#222", fg="white").pack(fill=tk.X)

    def show_last_packet_hex(self):
        self.hex_view.delete(1.0, tk.END)
        if self.captured_packets:
            pkt = self.captured_packets[-1]
            dump = hexdump(pkt, dump=True)
            self.hex_view.insert(tk.END, f"Packet Summary: {pkt.summary()}\n\n")
            self.hex_view.insert(tk.END, dump)
        else:
            self.hex_view.insert(tk.END, "No packets captured yet.")

    # --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ И ОЧЕРЕДИ ---
    def create_input(self, parent, label, default):
        tk.Label(parent, text=label, bg="#111", fg="#888").pack(anchor="w", padx=10)
        e = tk.Entry(parent, bg="#222", fg="white", insertbackground="white")
        e.insert(0, default)
        e.pack(fill=tk.X, padx=10, pady=(0, 10))
        return e

    def log(self, message, tag="INFO"):
        self.gui_queue.put(("LOG", (message, tag)))

    def _trim_console(self):
        line_count = int(self.console.index('end-1c').split('.')[0])
        if line_count > MAX_CONSOLE_LINES:
            self.console.delete('1.0', f'{line_count - MAX_CONSOLE_LINES}.0')

    def process_queue(self):
        try:
            for _ in range(50):
                task = self.gui_queue.get_nowait()
                msg_type = task[0]
                data = task[1]

                if msg_type == "LOG":
                    text, tag = data
                    timestamp = datetime.now().strftime("[%H:%M:%S]")
                    self.console.insert(tk.END, f"{timestamp} {text}\n", tag)
                    self.console.see(tk.END)

                elif msg_type == "DRAW_MAP":
                    self.draw_network_map(data)
                    self.log(f"Map updated. Found {len(data)} nodes.", "INFO")

        except queue.Empty:
            pass
        finally:
            self._trim_console()
            self.root.after(100, self.process_queue)

    # --- ФУНКЦИОНАЛ (SNIFFER, GEOIP, REPORT) ---
    def toggle_sniffer(self):
        if not self.is_sniffing:
            self.is_sniffing = True
            self.btn_sniff.config(text="STOP SNIFFER", bg="red")
            threading.Thread(target=self._sniffer_thread, daemon=True).start()
        else:
            self.is_sniffing = False
            self.btn_sniff.config(text="START SNIFFER", bg="#003300")

    def _sniffer_thread(self):
        self.log("Sniffer started...", "INFO")
        target_ip = self.entry_ip.get().strip()
        router_ip = self.entry_router_ip.get().strip()
        self.log(f"Analytics filter: TARGET={target_ip} ROUTER={router_ip}", "INFO")

        with self.analytics_lock:
            self._sniff_start_time = time.time()

        def handler(pkt):
            if not self.is_sniffing:
                return
            self.captured_packets.append(pkt)
            if IP in pkt:
                relevant = self._collect_analytics(pkt, target_ip, router_ip)
                if relevant:
                    with self.analytics_lock:
                        packet_count = self.analytics["total_packets"]
                    if packet_count % 20 == 0:
                        msg = f"{pkt[IP].src} -> {pkt[IP].dst} : {pkt.summary()}"
                        self.gui_queue.put(("LOG", (msg, "DATA")))

        try:
            sniff(prn=handler, store=False, stop_filter=lambda x: not self.is_sniffing)
        except Exception as e:
            self.gui_queue.put(("LOG", (f"Sniffer error: {e}. Try running as Administrator.", "ALERT")))
        self.log("Sniffer stopped.", "INFO")

    def run_geoip(self):  # НОВОВВЕДЕНИЕ 3
        target = self.entry_ip.get()
        self.log(f"Locating {target}...", "INFO")

        def _geo_thread():
            try:
                if requests:
                    response = requests.get(f"http://ip-api.com/json/{target}").json()
                    if response['status'] == 'success':
                        info = f"Country: {response['country']}\nCity: {response['city']}\nISP: {response['isp']}"
                        self.gui_queue.put(("LOG", (f"\n[GEOIP RESULT]\n{info}\n", "INFO")))
                    else:
                        self.gui_queue.put(("LOG", ("GeoIP failed: Private IP or Invalid", "ALERT")))
                else:
                    self.gui_queue.put(("LOG", ("Module 'requests' not installed.", "ALERT")))
            except Exception as e:
                self.gui_queue.put(("LOG", (f"GeoIP Error: {e}", "ALERT")))

        threading.Thread(target=_geo_thread, daemon=True).start()

    def generate_report(self):  # НОВОВВЕДЕНИЕ 5
        filename = f"report_{int(time.time())}.html"
        analytics = self._snapshot_analytics()
        top_peers_html = "".join(
            f"<li>{ip}: packets={row['packets']}, bytes={row['bytes']}</li>"
            for ip, row in analytics["top_peers"]
        ) or "<li>No data</li>"
        html = f"""
        <html>
        <body style="background:black; color:#00FF00; font-family:monospace;">
            <h1>PASHCHENKO SECURITY REPORT</h1>
            <hr>
            <h2>Target: {self.entry_ip.get()}</h2>
            <h2>Router: {self.entry_router_ip.get()}</h2>
            <h3>Packets Captured: {len(self.captured_packets)}</h3>
            <h3>Relevant Packets (Target/Router): {analytics['total_packets']}</h3>
            <h3>Total Bytes: {analytics['total_bytes']}</h3>
            <h3>Time: {datetime.now()}</h3>
            <hr>
            <h2>Protocols</h2>
            <pre>{json.dumps(analytics['protocols'], indent=2)}</pre>
            <h2>Top Peers</h2>
            <ul>{top_peers_html}</ul>
            <hr>
            <p>Generated by Pashchenko Cyber Suite v7.0</p>
        </body>
        </html>
        """

        try:
            with open(filename, "w") as f:
                f.write(html)
            self.log(f"Report saved to {filename}", "INFO")
            os.system(f"start {filename}")  # Открывает файл (для Windows)
        except Exception as e:
            self.log(f"Error saving report: {e}", "ALERT")

    # --- АНАЛИТИКА ---
    def _new_analytics_state(self):
        return {
            "total_packets": 0,
            "total_bytes": 0,
            "protocols": defaultdict(int),
            "tcp_flags": defaultdict(int),
            "dns_queries": defaultdict(int),
            "peers": defaultdict(lambda: {
                "packets": 0,
                "bytes": 0,
                "to_target": 0,
                "from_target": 0,
                "via_router": 0,
            }),
            "bandwidth_log": deque(maxlen=300),
        }

    def reset_analytics(self):
        with self.analytics_lock:
            self.analytics = self._new_analytics_state()
            self._sniff_start_time = time.time() if self.is_sniffing else None
        self._do_render_analytics()
        self.log("Analytics reset.", "INFO")

    def _schedule_analytics_refresh(self):
        self._do_render_analytics()
        self._analytics_refresh_id = self.root.after(
            ANALYTICS_REFRESH_MS, self._schedule_analytics_refresh
        )

    def _proto_name(self, pkt):
        if TCP in pkt:
            return "TCP"
        if UDP in pkt:
            return "UDP"
        if ARP in pkt:
            return "ARP"
        return "OTHER"

    @staticmethod
    def _fmt_bytes(n):
        for unit in ('B', 'KB', 'MB', 'GB'):
            if abs(n) < 1024:
                return f"{n:.1f} {unit}"
            n /= 1024
        return f"{n:.1f} TB"

    @staticmethod
    def _fmt_duration(sec):
        sec = int(sec)
        h, rem = divmod(sec, 3600)
        m, s = divmod(rem, 60)
        if h:
            return f"{h}h {m}m {s}s"
        if m:
            return f"{m}m {s}s"
        return f"{s}s"

    def _collect_analytics(self, pkt, target_ip, router_ip):
        if IP not in pkt:
            return False

        src = pkt[IP].src
        dst = pkt[IP].dst
        is_relevant = target_ip in (src, dst) or router_ip in (src, dst)
        if not is_relevant:
            return False

        proto = self._proto_name(pkt)
        size = len(pkt)
        now = time.time()

        with self.analytics_lock:
            a = self.analytics
            a["total_packets"] += 1
            a["total_bytes"] += size
            a["protocols"][proto] += 1
            a["bandwidth_log"].append((now, size))

            if TCP in pkt:
                flags = str(pkt[TCP].flags)
                a["tcp_flags"][flags] += 1

            if pkt.haslayer(DNS) and pkt.haslayer(DNSQR):
                try:
                    qname = pkt[DNSQR].qname
                    if isinstance(qname, bytes):
                        qname = qname.decode(errors='ignore')
                    qname = qname.rstrip('.')
                    if qname:
                        a["dns_queries"][qname] += 1
                except Exception:
                    pass

            peer_ip = None
            peer = None
            if src == target_ip:
                peer_ip = dst
                peer = a["peers"][peer_ip]
                peer["from_target"] += 1
            elif dst == target_ip:
                peer_ip = src
                peer = a["peers"][peer_ip]
                peer["to_target"] += 1
            elif src == router_ip:
                peer_ip = dst
                peer = a["peers"][peer_ip]
            elif dst == router_ip:
                peer_ip = src
                peer = a["peers"][peer_ip]

            if peer is not None:
                peer["packets"] += 1
                peer["bytes"] += size
                if router_ip in (src, dst):
                    peer["via_router"] += 1

        return True

    def _calc_bandwidth(self):
        now = time.time()
        cutoff = now - BANDWIDTH_WINDOW_SEC
        with self.analytics_lock:
            bw_log = self.analytics["bandwidth_log"]
            total = sum(size for ts, size in bw_log if ts >= cutoff)
        elapsed = min(BANDWIDTH_WINDOW_SEC, now - (self._sniff_start_time or now))
        if elapsed <= 0:
            return 0.0
        return total / elapsed

    def _snapshot_analytics(self):
        with self.analytics_lock:
            protocols = dict(self.analytics["protocols"])
            tcp_flags = dict(self.analytics["tcp_flags"])
            dns_queries = dict(self.analytics["dns_queries"])
            peers = {ip: dict(stats) for ip, stats in self.analytics["peers"].items()}
            total_packets = self.analytics["total_packets"]
            total_bytes = self.analytics["total_bytes"]
            start_time = self._sniff_start_time

        top_peers = sorted(peers.items(), key=lambda item: item[1]["bytes"], reverse=True)[:10]
        top_dns = sorted(dns_queries.items(), key=lambda item: item[1], reverse=True)[:8]
        bps = self._calc_bandwidth()
        uptime = (time.time() - start_time) if start_time else 0

        return {
            "total_packets": total_packets,
            "total_bytes": total_bytes,
            "protocols": protocols,
            "tcp_flags": tcp_flags,
            "top_dns": top_dns,
            "top_peers": top_peers,
            "bandwidth_bps": bps,
            "uptime": uptime,
        }

    def _do_render_analytics(self):
        data = self._snapshot_analytics()
        self.render_analytics(data)

    def render_analytics(self, data):
        sniffer_status = "ACTIVE" if self.is_sniffing else "STOPPED"
        uptime_str = self._fmt_duration(data.get('uptime', 0))
        bw = self._fmt_bytes(data.get('bandwidth_bps', 0))

        lines = [
            f"=== LIVE TRAFFIC ANALYTICS  [{sniffer_status}]  Uptime: {uptime_str} ===",
            f"Target: {self.entry_ip.get().strip()}   Router: {self.entry_router_ip.get().strip()}",
            f"Packets: {data['total_packets']}   Bytes: {self._fmt_bytes(data['total_bytes'])}   Bandwidth: {bw}/s",
            "",
            "--- Protocols ---",
        ]
        if data["protocols"]:
            proto_parts = []
            for proto, count in sorted(data["protocols"].items(), key=lambda x: x[1], reverse=True):
                pct = (count / data['total_packets'] * 100) if data['total_packets'] else 0
                proto_parts.append(f"{proto}: {count} ({pct:.0f}%)")
            lines.append("  " + "  |  ".join(proto_parts))
        else:
            lines.append("  No data")

        if data.get("tcp_flags"):
            lines.append("")
            lines.append("--- TCP Flags ---")
            flag_parts = [f"{flag}: {cnt}" for flag, cnt in
                          sorted(data["tcp_flags"].items(), key=lambda x: x[1], reverse=True)[:6]]
            lines.append("  " + "  |  ".join(flag_parts))

        if data.get("top_dns"):
            lines.append("")
            lines.append("--- DNS Queries (top) ---")
            for domain, cnt in data["top_dns"]:
                lines.append(f"  {domain}: {cnt}")

        lines.append("")
        lines.append("--- Top Peers (by traffic) ---")
        if data["top_peers"]:
            for ip, row in data["top_peers"]:
                lines.append(
                    f"  {ip:>15s}  {self._fmt_bytes(row['bytes']):>10s}  "
                    f"pkts={row['packets']}  in={row['to_target']}  out={row['from_target']}  router={row['via_router']}"
                )
        else:
            lines.append("  No data")

        try:
            self.analytics_view.config(state=tk.NORMAL)
            self.analytics_view.delete(1.0, tk.END)
            self.analytics_view.insert(tk.END, "\n".join(lines))
            self.analytics_view.config(state=tk.DISABLED)
        except tk.TclError:
            pass


if __name__ == "__main__":
    root = tk.Tk()
    # DPI Fix
    try:
        from ctypes import windll

        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass

    app = PashchenkoCyberSuite(root)
    root.mainloop()