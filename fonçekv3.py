"""
FVT / TEFAS FON TAKİP - Masaüstü GUI
Gereksinim: pip install customtkinter requests
EXE: pyinstaller --onefile --windowed FonTakip_GUI.py
"""

import threading
import requests
import customtkinter as ctk
from tkinter import ttk, messagebox
import tkinter as tk
from datetime import datetime

# Tema ayarları
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

NAVY   = "#1a3c5e"
MID    = "#2e6da4"
LIGHT  = "#ebf3fb"
GREEN  = "#16a34a"
RED    = "#dc2626"
GRAY   = "#64748b"
BG     = "#f1f5f9"
WHITE  = "#ffffff"

BASE_URL = "https://fvt.com.tr"
HEADERS  = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://fvt.com.tr/",
    "Origin": "https://fvt.com.tr"
}

# ─────────────────────────────────────────────
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("TEFAS / FVT Fon Takip")
        self.geometry("1400x750")
        self.minsize(900, 600)
        self.configure(fg_color=BG)

        self.secili_fonlar = []   # Seçili fon kodları
        self.tum_veri      = []   # Tablo verisi
        self.arama_timer   = None

        self._arayuz_olustur()

    # ── ARAYÜZ ────────────────────────────────
    def _arayuz_olustur(self):
        # BAŞLIK
        baslik = ctk.CTkFrame(self, fg_color=NAVY, height=55, corner_radius=0)
        baslik.pack(fill="x")
        baslik.pack_propagate(False)
        ctk.CTkLabel(baslik, text="  📊  TEFAS / FVT FON TAKİP PANELİ",
                     font=("Arial", 14, "bold"), text_color="white").pack(side="left", padx=16)
        self.lbl_guncelleme = ctk.CTkLabel(baslik, text="Henüz güncellenmedi",
                                            font=("Arial", 10), text_color="#94a3b8")
        self.lbl_guncelleme.pack(side="right", padx=16)

        # KONTROL PANELİ
        kontrol = ctk.CTkFrame(self, fg_color=WHITE, corner_radius=0, height=130)
        kontrol.pack(fill="x")
        kontrol.pack_propagate(False)
        inner = ctk.CTkFrame(kontrol, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=16, pady=10)

        # Sol: Arama
        arama_frame = ctk.CTkFrame(inner, fg_color="transparent")
        arama_frame.pack(side="left", fill="both", expand=True)

        ctk.CTkLabel(arama_frame, text="FON ARA", font=("Arial", 10, "bold"),
                     text_color=GRAY).pack(anchor="w")

        self.ara_entry = ctk.CTkEntry(arama_frame, placeholder_text="Fon adı veya kodu yazın... (örn: Tera, TLY, Garanti)",
                                      width=400, height=36, font=("Arial", 12))
        self.ara_entry.pack(anchor="w", pady=(3,0))
        self.ara_entry.bind("<KeyRelease>", self._arama_tetikle)
        self.ara_entry.bind("<Down>",       self._dd_asagi)
        self.ara_entry.bind("<Up>",         self._dd_yukari)
        self.ara_entry.bind("<Return>",     self._dd_sec)
        self.ara_entry.bind("<Escape>",     lambda e: self._dd_kapat())

        ctk.CTkLabel(arama_frame, text="Yazın, listeden seçin. ↑↓ Enter ile de seçebilirsiniz.",
                     font=("Arial", 10), text_color=GRAY).pack(anchor="w", pady=(2,0))

        # Dropdown (Toplevel pencere)
        self.dropdown_win = None
        self.dd_listbox   = None
        self.dd_sonuclar  = []

        # Orta: Seçili fonlar
        secili_frame = ctk.CTkFrame(inner, fg_color="transparent")
        secili_frame.pack(side="left", fill="both", expand=True, padx=20)

        ctk.CTkLabel(secili_frame, text="SEÇİLİ FONLAR", font=("Arial", 10, "bold"),
                     text_color=GRAY).pack(anchor="w")

        self.secili_liste = tk.Listbox(secili_frame, height=4, font=("Consolas", 11),
                                        selectbackground=LIGHT, selectforeground=NAVY,
                                        bg=BG, relief="flat", bd=1, highlightthickness=1,
                                        highlightcolor=MID, activestyle="none")
        self.secili_liste.pack(fill="both", expand=True, pady=(3,0))
        self.secili_liste.bind("<Delete>",     self._seciliyi_sil)
        self.secili_liste.bind("<BackSpace>",  self._seciliyi_sil)

        ctk.CTkLabel(secili_frame, text="Delete tuşu ile listeden çıkarabilirsiniz",
                     font=("Arial", 10), text_color=GRAY).pack(anchor="w", pady=(2,0))

        # Sağ: Butonlar
        btn_frame = ctk.CTkFrame(inner, fg_color="transparent")
        btn_frame.pack(side="right", padx=10)

        self.btn_guncelle = ctk.CTkButton(btn_frame, text="🔄  Güncelle",
                                           command=self._guncelle_baslat,
                                           fg_color=NAVY, hover_color=MID,
                                           font=("Arial", 13, "bold"), width=140, height=36)
        self.btn_guncelle.pack(pady=3)

        ctk.CTkButton(btn_frame, text="⬇  CSV İndir", command=self._csv_indir,
                      fg_color=BG, text_color=NAVY, border_color="#cbd5e1", border_width=1,
                      hover_color=LIGHT, font=("Arial", 12), width=140, height=32).pack(pady=3)

        ctk.CTkButton(btn_frame, text="🗑  Temizle", command=self._temizle,
                      fg_color=BG, text_color=NAVY, border_color="#cbd5e1", border_width=1,
                      hover_color=LIGHT, font=("Arial", 12), width=140, height=32).pack(pady=3)

        # ÖZET KARTLAR
        self.ozet_frame = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        self.ozet_frame.pack(fill="x", padx=16, pady=(8,0))
        self.ozet_etiketler = {}
        for baslik, key in [("Toplam", "toplam"), ("Başarılı", "basarili"),
                             ("Hatalı", "hatali"), ("Günlük (+)", "pos"), ("Günlük (-)", "neg")]:
            kart = ctk.CTkFrame(self.ozet_frame, fg_color=WHITE, corner_radius=10)
            kart.pack(side="left", padx=4, pady=4, ipadx=12, ipady=6)
            ctk.CTkLabel(kart, text=baslik, font=("Arial", 9, "bold"), text_color=GRAY).pack()
            lbl = ctk.CTkLabel(kart, text="0", font=("Arial", 20, "bold"), text_color=NAVY)
            lbl.pack()
            self.ozet_etiketler[key] = lbl

        # PROGRESS BAR
        self.progress_frame = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        self.progress_frame.pack(fill="x", padx=16, pady=(4,0))
        self.progress_bar  = ctk.CTkProgressBar(self.progress_frame, mode="determinate",
                                                  progress_color=MID, height=6)
        self.progress_bar.pack(fill="x")
        self.progress_bar.set(0)
        self.lbl_progress = ctk.CTkLabel(self.progress_frame, text="",
                                          font=("Arial", 10), text_color=GRAY)
        self.lbl_progress.pack(anchor="w")
        self.progress_frame.pack_forget()

        # TABLO
        tablo_frame = ctk.CTkFrame(self, fg_color=WHITE, corner_radius=8)
        tablo_frame.pack(fill="both", expand=True, padx=16, pady=8)

        # Filtre + sayı
        filtre_bar = ctk.CTkFrame(tablo_frame, fg_color="transparent")
        filtre_bar.pack(fill="x", padx=8, pady=(6,2))
        self.lbl_sayi = ctk.CTkLabel(filtre_bar, text="", font=("Arial", 11), text_color=GRAY)
        self.lbl_sayi.pack(side="left")
        self.filtre_entry = ctk.CTkEntry(filtre_bar, placeholder_text="Tabloda ara...",
                                          width=200, height=28, font=("Arial", 11))
        self.filtre_entry.pack(side="right")
        self.filtre_entry.bind("<KeyRelease>", lambda e: self._tabloyu_guncelle())

        # Treeview
        sutunlar = ("kod","ad","fiyat","gunluk","haftalik","ytd","1ay","3ay","6ay",
                    "1yil","3yil","5yil","yatirimci","portfoy","kategori","tarih")
        basliklar = ("Kod","Fon Adı","Fiyat (TL)","Günlük %","Haftalık %","YTD %",
                     "1 Ay %","3 Ay %","6 Ay %","1 Yıl %","3 Yıl %","5 Yıl %",
                     "Yatırımcı","Portföy (TL)","Kategori","Tarih")
        genislikler = (65,260,100,80,80,80,80,80,80,85,85,90,100,110,120,90)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Fon.Treeview",
                         background=WHITE, foreground="#1e293b",
                         rowheight=28, fieldbackground=WHITE,
                         font=("Segoe UI", 10), borderwidth=0)
        style.configure("Fon.Treeview.Heading",
                         background=MID, foreground="white",
                         font=("Segoe UI", 10, "bold"), relief="flat", padding=6)
        style.map("Fon.Treeview",
                   background=[("selected", LIGHT)],
                   foreground=[("selected", NAVY)])
        style.map("Fon.Treeview.Heading",
                   background=[("active", NAVY)])

        scroll_y = ttk.Scrollbar(tablo_frame, orient="vertical")
        scroll_x = ttk.Scrollbar(tablo_frame, orient="horizontal")

        self.tablo = ttk.Treeview(tablo_frame, columns=sutunlar, show="headings",
                                   style="Fon.Treeview", yscrollcommand=scroll_y.set,
                                   xscrollcommand=scroll_x.set, selectmode="browse")
        scroll_y.config(command=self.tablo.yview)
        scroll_x.config(command=self.tablo.xview)

        for s, b, g in zip(sutunlar, basliklar, genislikler):
            self.tablo.heading(s, text=b, command=lambda c=s: self._sirala(c))
            self.tablo.column(s, width=g, minwidth=50, anchor="center")
        self.tablo.column("ad", anchor="w")

        # Zebra + renk tagleri
        self.tablo.tag_configure("cift",  background="#f8fafc")
        self.tablo.tag_configure("tek",   background=WHITE)
        self.tablo.tag_configure("hata",  foreground=RED)
        self.tablo.tag_configure("yukleniyor", foreground=GRAY)

        scroll_y.pack(side="right",  fill="y")
        scroll_x.pack(side="bottom", fill="x")
        self.tablo.pack(fill="both", expand=True, padx=4, pady=2)

        self._siralama = {s: False for s in sutunlar}

    # ── DROPDOWN ────────────────────────────────
    def _arama_tetikle(self, event):
        if event.keysym in ("Up", "Down", "Return", "Escape"): return
        if self.arama_timer: self.after_cancel(self.arama_timer)
        q = self.ara_entry.get().strip()
        if len(q) < 2:
            self._dd_kapat()
            return
        self.arama_timer = self.after(300, lambda: threading.Thread(
            target=self._arama_yap, args=(q,), daemon=True).start())

    def _arama_yap(self, q):
        try:
            r = requests.get(f"{BASE_URL}/api/funds",
                             params={"search": q, "limit": 15},
                             headers=HEADERS, timeout=8)
            m = r.json()
            liste = m.get("data", {}).get("data", []) if m.get("success") else []
            self.after(0, lambda: self._dd_goster(liste))
        except Exception as e:
            self.after(0, lambda: self._dd_goster([]))

    def _dd_goster(self, liste):
        self._dd_kapat()
        self.dd_sonuclar = liste
        if not liste:
            return

        # Dropdown penceresi
        x = self.ara_entry.winfo_rootx()
        y = self.ara_entry.winfo_rooty() + self.ara_entry.winfo_height() + 2
        w = max(self.ara_entry.winfo_width(), 420)

        self.dropdown_win = tk.Toplevel(self)
        self.dropdown_win.wm_overrideredirect(True)
        self.dropdown_win.geometry(f"{w}x{min(len(liste)*32+4, 240)}+{x}+{y}")
        self.dropdown_win.configure(bg=WHITE)
        self.dropdown_win.attributes("-topmost", True)

        frame = tk.Frame(self.dropdown_win, bg=WHITE, bd=1, relief="solid")
        frame.pack(fill="both", expand=True)

        self.dd_listbox = tk.Listbox(frame, font=("Consolas", 11),
                                      selectbackground=LIGHT, selectforeground=NAVY,
                                      bg=WHITE, relief="flat", bd=0,
                                      activestyle="none", cursor="hand2")
        self.dd_listbox.pack(fill="both", expand=True)

        for f in liste:
            kod = f.get("fonKodu", "")
            ad  = f.get("fonAdi", "")
            kat = f.get("kategori", "")
            ekli = "✓ " if kod in self.secili_fonlar else "  "
            ad_kisalt = ad[:45] + "..." if len(ad) > 45 else ad
            self.dd_listbox.insert("end", f"{ekli}{kod:<8} {ad_kisalt}  [{kat}]")

        self.dd_listbox.bind("<ButtonRelease-1>", self._dd_tikla)
        self.dd_listbox.bind("<Return>", self._dd_sec)

        # Dışarı tıklayınca kapat
        self.dropdown_win.bind("<FocusOut>", lambda e: self.after(150, self._dd_kapat))

    def _dd_kapat(self):
        if self.dropdown_win:
            try: self.dropdown_win.destroy()
            except: pass
            self.dropdown_win = None
            self.dd_listbox   = None

    def _dd_asagi(self, event):
        if self.dd_listbox:
            sel = self.dd_listbox.curselection()
            idx = (sel[0] + 1) if sel else 0
            idx = min(idx, self.dd_listbox.size() - 1)
            self.dd_listbox.selection_clear(0, "end")
            self.dd_listbox.selection_set(idx)
            self.dd_listbox.see(idx)

    def _dd_yukari(self, event):
        if self.dd_listbox:
            sel = self.dd_listbox.curselection()
            idx = (sel[0] - 1) if sel else 0
            idx = max(idx, 0)
            self.dd_listbox.selection_clear(0, "end")
            self.dd_listbox.selection_set(idx)
            self.dd_listbox.see(idx)

    def _dd_sec(self, event=None):
        if self.dd_listbox:
            sel = self.dd_listbox.curselection()
            if sel:
                self._dd_ekle(sel[0])

    def _dd_tikla(self, event):
        if self.dd_listbox:
            idx = self.dd_listbox.nearest(event.y)
            self._dd_ekle(idx)

    def _dd_ekle(self, idx):
        if idx < 0 or idx >= len(self.dd_sonuclar): return
        f   = self.dd_sonuclar[idx]
        kod = f.get("fonKodu", "")
        if not kod or kod in self.secili_fonlar: return
        self.secili_fonlar.append(kod)
        self._secili_listesini_guncelle()
        self.ara_entry.delete(0, "end")
        self._dd_kapat()

    # ── SEÇİLİ LİSTE ────────────────────────────
    def _secili_listesini_guncelle(self):
        self.secili_liste.delete(0, "end")
        for i, kod in enumerate(self.secili_fonlar):
            self.secili_liste.insert("end", f"  {kod}")
            self.secili_liste.itemconfig(i, fg=NAVY, selectforeground=NAVY)

    def _seciliyi_sil(self, event=None):
        sel = self.secili_liste.curselection()
        if not sel: return
        idx = sel[0]
        self.secili_fonlar.pop(idx)
        self._secili_listesini_guncelle()

    # ── VERİ ÇEKME ──────────────────────────────
    def _guncelle_baslat(self):
        if not self.secili_fonlar:
            messagebox.showinfo("Uyarı", "Önce fon arayıp listeden seçin.")
            return
        self.btn_guncelle.configure(state="disabled", text="Yükleniyor...")
        self.progress_frame.pack(fill="x", padx=16, pady=(4,0))
        self.progress_bar.set(0)
        threading.Thread(target=self._veri_cek, daemon=True).start()

    def _veri_cek(self):
        kodlar = self.secili_fonlar[:]
        toplam = len(kodlar)
        sonuclar = [None] * toplam
        b = h = pos = neg = 0

        for i, kod in enumerate(kodlar):
            # Placeholder göster
            self.after(0, lambda i=i, k=kod: self._satir_guncelle(i, k, None, True))

            try:
                r = requests.get(f"{BASE_URL}/api/funds/{kod}",
                                  headers=HEADERS, timeout=20)
                m = r.json()
                if m.get("success") and m.get("data"):
                    f   = m["data"]["fund"]
                    ret = m["data"].get("returns", {})
                    p   = lambda v: float(v) if v not in (None, "", "null") else None
                    row = {
                        "kod":       kod,
                        "err":       False,
                        "ad":        f.get("fonAdi", "-"),
                        "fiyat":     p(f.get("fiyat")),
                        "gunluk":    p(f.get("getiri")),
                        "haftalik":  p(ret.get("haftalikGetiri")),
                        "ytd":       p(ret.get("ytdGetiri")),
                        "ay1":       p(ret.get("aylikGetiri")),
                        "ay3":       p(ret.get("ucAylikGetiri")),
                        "ay6":       p(ret.get("altiAylikGetiri")),
                        "yil1":      p(ret.get("birYillikGetiri")),
                        "yil3":      p(ret.get("ucYillikGetiri")),
                        "yil5":      p(ret.get("besYillikGetiri")),
                        "yatirimci": int(f.get("yatirimci") or 0) or None,
                        "portfoy":   p(f.get("toplamDeger")),
                        "kategori":  f.get("kategori", "-"),
                        "tarih":     (f.get("sonGuncelleme") or "")[:10]
                    }
                    b += 1
                    if row["gunluk"] and row["gunluk"] > 0: pos += 1
                    if row["gunluk"] and row["gunluk"] < 0: neg += 1
                else:
                    row = {"kod": kod, "err": True, "ad": "Veri alınamadı"}
                    h += 1
            except Exception as e:
                row = {"kod": kod, "err": True, "ad": str(e)[:60]}
                h += 1

            sonuclar[i] = row
            pct = (i + 1) / toplam

            self.after(0, lambda i=i, r=row, p=pct, k=kod, idx=i+1, t=toplam:
                       self._satir_guncelle(i, k, r, False) or
                       self._progress_guncelle(p, f"{idx}/{t} - {k}"))

        self.tum_veri = [r for r in sonuclar if r]
        self.after(0, lambda: self._bitti(b, h, pos, neg, toplam))

    def _satir_guncelle(self, idx, kod, row, yukleniyor):
        # Tablo satırını güncelle (item ID'ye göre)
        item_id = f"row_{idx}"
        if self.tablo.exists(item_id):
            self.tablo.delete(item_id)

        renk_tag = "cift" if idx % 2 == 0 else "tek"

        if yukleniyor:
            self.tablo.insert("", idx, iid=item_id,
                               values=(kod, "yükleniyor...", *[""] * 14),
                               tags=("yukleniyor",))
            return

        if row["err"]:
            self.tablo.insert("", idx, iid=item_id,
                               values=(row["kod"], row["ad"], *["HATA"] * 14),
                               tags=("hata",))
            return

        def fmt_pct(v):
            if v is None: return "-"
            return f"+{v:.2f}%" if v > 0 else f"{v:.2f}%"

        def fmt_fiyat(v):
            if v is None: return "-"
            return f"{v:,.4f}".replace(",", ".")

        def fmt_buyuk(v):
            if not v: return "-"
            if v >= 1e9: return f"{v/1e9:.2f}B"
            if v >= 1e6: return f"{v/1e6:.1f}M"
            if v >= 1e3: return f"{v/1e3:.0f}K"
            return str(int(v))

        degerler = (
            row["kod"],
            row["ad"],
            fmt_fiyat(row["fiyat"]),
            fmt_pct(row["gunluk"]),
            fmt_pct(row["haftalik"]),
            fmt_pct(row["ytd"]),
            fmt_pct(row["ay1"]),
            fmt_pct(row["ay3"]),
            fmt_pct(row["ay6"]),
            fmt_pct(row["yil1"]),
            fmt_pct(row["yil3"]),
            fmt_pct(row["yil5"]),
            f"{row['yatirimci']:,}".replace(",",".") if row["yatirimci"] else "-",
            fmt_buyuk(row["portfoy"]),
            row["kategori"],
            row["tarih"]
        )
        self.tablo.insert("", idx, iid=item_id, values=degerler, tags=(renk_tag,))

        # Pozitif/negatif renk (tag override)
        if row["gunluk"] and row["gunluk"] > 0:
            self.tablo.tag_configure(item_id + "_g", foreground=GREEN)
        elif row["gunluk"] and row["gunluk"] < 0:
            self.tablo.tag_configure(item_id + "_r", foreground=RED)

    def _progress_guncelle(self, pct, metin):
        self.progress_bar.set(pct)
        self.lbl_progress.configure(text=metin)

    def _bitti(self, b, h, pos, neg, toplam):
        self.ozet_etiketler["toplam"].configure(text=str(toplam))
        self.ozet_etiketler["basarili"].configure(text=str(b), text_color=GREEN)
        self.ozet_etiketler["hatali"].configure(text=str(h),   text_color=RED if h else NAVY)
        self.ozet_etiketler["pos"].configure(text=str(pos), text_color=GREEN)
        self.ozet_etiketler["neg"].configure(text=str(neg), text_color=RED if neg else NAVY)
        self.lbl_sayi.configure(text=f"{b} fon yüklendi")
        self.lbl_guncelleme.configure(
            text=f"Son güncelleme: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}  |  fvt.com.tr")
        self.progress_frame.pack_forget()
        self.btn_guncelle.configure(state="normal", text="🔄  Güncelle")

    # ── TABLO FİLTRE / SIRALA ───────────────────
    def _tabloyu_guncelle(self):
        q = self.filtre_entry.get().strip().lower()
        for item in self.tablo.get_children():
            vals = self.tablo.item(item, "values")
            if q in " ".join(str(v).lower() for v in vals):
                self.tablo.reattach(item, "", "end")
            else:
                self.tablo.detach(item)

    def _sirala(self, sutun):
        items = [(self.tablo.set(k, sutun), k) for k in self.tablo.get_children("")]
        artan = self._siralama[sutun]
        try:
            items.sort(key=lambda x: float(x[0].replace("%","").replace("+","").replace(",",".") or "0"), reverse=not artan)
        except:
            items.sort(key=lambda x: x[0], reverse=not artan)
        for i, (_, k) in enumerate(items):
            self.tablo.move(k, "", i)
        self._siralama[sutun] = not artan

    # ── CSV ─────────────────────────────────────
    def _csv_indir(self):
        if not self.tum_veri:
            messagebox.showinfo("Uyarı", "Önce veri yükleyin.")
            return
        from tkinter import filedialog
        dosya = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile=f"fon-takip-{datetime.now().strftime('%Y-%m-%d')}.csv")
        if not dosya: return
        basliklar = ["Kod","Fon Adı","Fiyat","Günlük%","Haftalık%","YTD%",
                     "1Ay%","3Ay%","6Ay%","1Yıl%","3Yıl%","5Yıl%",
                     "Yatırımcı","Portföy","Kategori","Tarih"]
        satirlar = []
        for r in self.tum_veri:
            if r.get("err"): continue
            satirlar.append([
                r["kod"], r["ad"], r["fiyat"], r["gunluk"], r["haftalik"],
                r["ytd"], r["ay1"], r["ay3"], r["ay6"], r["yil1"], r["yil3"],
                r["yil5"], r["yatirimci"], r["portfoy"], r["kategori"], r["tarih"]
            ])
        with open(dosya, "w", encoding="utf-8-sig") as f:
            f.write(";".join(basliklar) + "\n")
            for s in satirlar:
                f.write(";".join(str(v) if v is not None else "" for v in s) + "\n")
        messagebox.showinfo("Tamam", f"CSV kaydedildi:\n{dosya}")

    # ── TEMİZLE ─────────────────────────────────
    def _temizle(self):
        self.tum_veri = []
        self.secili_fonlar = []
        self._secili_listesini_guncelle()
        for item in self.tablo.get_children():
            self.tablo.delete(item)
        self.lbl_sayi.configure(text="")
        self.lbl_guncelleme.configure(text="Henüz güncellenmedi")
        for k in self.ozet_etiketler:
            self.ozet_etiketler[k].configure(text="0", text_color=NAVY)


if __name__ == "__main__":
    app = App()
    app.mainloop()
