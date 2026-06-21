import datetime
import threading
from tkinter import messagebox, ttk

import customtkinter as ctk
import requests
from PIL import Image

from controllers.auth import AuthController
from controllers.library import (
    BookController,
    BorrowController,
    MemberController,
    NotificationController,
    RequestController,
)
from controllers.validators import first_valid_isbn
from models.database import check_integrity, refresh_catalog_metadata
from views.theme import (
    ACCENT,
    BACKGROUND,
    BORDER,
    DANGER,
    FONT_FAMILY,
    GLASS,
    GLASS_BORDER,
    GLASS_HOVER,
    GLASS_MUTED,
    INPUT,
    PANEL,
    PRIMARY,
    PRIMARY_HOVER,
    RADIUS_LARGE,
    SIDEBAR,
    SUCCESS,
    TEXT,
    TEXT_MUTED,
    WARNING,
    icon_path,
)

APPLE_BG = BACKGROUND
APPLE_PANEL = PANEL
APPLE_BLUE = PRIMARY
APPLE_GREEN = SUCCESS
APPLE_RED = DANGER
APPLE_ORANGE = WARNING
APPLE_TEXT = TEXT
APPLE_TEXT_MUTED = TEXT_MUTED


def get_icon(name, size=20):
    try:
        l_img = Image.open(icon_path(f"{name}_b.png"))
        d_img = Image.open(icon_path(f"{name}_w.png"))
        return ctk.CTkImage(light_image=l_img, dark_image=d_img, size=(size, size))
    except (FileNotFoundError, OSError):
        return None


def get_single_icon(name, size=20):
    try:
        return ctk.CTkImage(light_image=Image.open(icon_path(name)), size=(size, size))
    except (FileNotFoundError, OSError):
        return None


def apply_treeview_style():
    style = ttk.Style()
    style.theme_use("default")
    mode = ctk.get_appearance_mode()
    bg = GLASS[0] if mode == "Light" else GLASS[1]
    fg = TEXT[0] if mode == "Light" else TEXT[1]
    h_bg = GLASS_MUTED[0] if mode == "Light" else GLASS_MUTED[1]
    sel_bg = PRIMARY[0] if mode == "Light" else PRIMARY[1]

    style.configure(
        "Treeview",
        rowheight=35,
        font=(FONT_FAMILY, 11),
        background=bg,
        fieldbackground=bg,
        foreground=fg,
        borderwidth=0,
    )
    style.configure(
        "Treeview.Heading", font=(FONT_FAMILY, 12, "bold"), background=h_bg, foreground=fg, borderwidth=0
    )
    style.map("Treeview", background=[("selected", sel_bg)])


class AnimatedButton(ctk.CTkButton):
    def __init__(self, master, fg_color=APPLE_BLUE, **kwargs):
        kwargs.setdefault("hover_color", PRIMARY_HOVER)
        super().__init__(master, fg_color=fg_color, corner_radius=11, border_spacing=8, **kwargs)


class GlassFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        cr = kwargs.pop("corner_radius", RADIUS_LARGE)
        fg_color = kwargs.pop("fg_color", GLASS)
        border_color = kwargs.pop("border_color", GLASS_BORDER)
        super().__init__(
            master,
            fg_color=fg_color,
            corner_radius=cr,
            border_width=1,
            border_color=border_color,
            **kwargs,
        )


class AdminLoginView(ctk.CTkFrame):
    def __init__(self, master, on_success):
        super().__init__(master, fg_color=APPLE_BG)
        self.on_success = on_success

        self.box = GlassFrame(self, width=450, height=550)
        self.box.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(self.box, text="⚙️ Yönetim", font=ctk.CTkFont(size=36, weight="bold")).pack(pady=(60, 40))

        self.user = ctk.CTkEntry(
            self.box, placeholder_text="Kullanıcı Adı", width=300, height=45, corner_radius=10
        )
        self.user.pack(pady=10)
        self.pwd = ctk.CTkEntry(
            self.box, placeholder_text="Şifre", show="●", width=300, height=45, corner_radius=10
        )
        self.pwd.pack(pady=10)

        self.btn = AnimatedButton(
            self.box,
            text="Giriş Yap",
            width=300,
            height=45,
            font=ctk.CTkFont(weight="bold"),
            command=self.login,
        )
        self.btn.pack(pady=30)

        self.err = ctk.CTkLabel(self.box, text="", text_color=APPLE_RED)
        self.err.pack()

    def login(self):
        success, admin_info = AuthController.login_admin(self.user.get(), self.pwd.get())
        if success:
            self.on_success(admin_info)
        else:
            self.err.configure(text="Hatalı bilgiler!")


class AdminDashboard(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=40, pady=(38, 20))
        title_group = ctk.CTkFrame(header, fg_color="transparent")
        title_group.pack(side="left")
        ctk.CTkLabel(title_group, text="Genel Bakış", font=ctk.CTkFont(size=32, weight="bold")).pack(
            anchor="w"
        )
        ctk.CTkLabel(
            title_group,
            text="Kütüphanenin canlı operasyon özeti",
            text_color=APPLE_TEXT_MUTED,
        ).pack(anchor="w", pady=(3, 0))
        AnimatedButton(header, text="↻ Yenile", width=100, command=self.refresh).pack(side="right")

        self.cards = ctk.CTkFrame(self, fg_color="transparent")
        self.cards.pack(fill="x", padx=40)

        self.lbl_tot = self.make_card("Katalog", "aktif eser", APPLE_BLUE)
        self.lbl_act = self.make_card("Dolaşım", "aktif ödünç", APPLE_ORANGE)
        self.lbl_members = self.make_card("Topluluk", "onaylı üye", APPLE_GREEN)
        self.lbl_pending = self.make_card("İş Kutusu", "bekleyen işlem", ACCENT)

        self.alert = GlassFrame(self, height=68, fg_color=GLASS_MUTED)
        self.alert.pack(fill="x", padx=50, pady=(22, 14))
        self.alert.pack_propagate(False)
        self.alert_icon = ctk.CTkLabel(self.alert, text="✓", font=ctk.CTkFont(size=22, weight="bold"))
        self.alert_icon.pack(side="left", padx=(22, 12))
        self.alert_text = ctk.CTkLabel(self.alert, text="", font=ctk.CTkFont(size=14, weight="bold"))
        self.alert_text.pack(side="left")

        self.activity = GlassFrame(self)
        self.activity.pack(fill="both", expand=True, padx=40, pady=(0, 36))
        ctk.CTkLabel(
            self.activity,
            text="Son Sistem Hareketleri",
            font=ctk.CTkFont(size=17, weight="bold"),
        ).pack(anchor="w", padx=22, pady=(18, 8))
        self.activity_list = ctk.CTkFrame(self.activity, fg_color="transparent")
        self.activity_list.pack(fill="both", expand=True, padx=18, pady=(0, 14))

        self.refresh()

    def make_card(self, title, subtitle, color):
        c = GlassFrame(self.cards, height=150)
        c.pack(side="left", fill="x", expand=True, padx=7)
        c.pack_propagate(False)
        ctk.CTkLabel(c, text=title.upper(), font=ctk.CTkFont(size=11, weight="bold"), text_color=color).pack(
            anchor="w", padx=20, pady=(20, 2)
        )
        lbl = ctk.CTkLabel(c, text="0", font=ctk.CTkFont(size=38, weight="bold"), text_color=APPLE_TEXT)
        lbl.pack(anchor="w", padx=20)
        ctk.CTkLabel(c, text=subtitle, font=ctk.CTkFont(size=11), text_color=APPLE_TEXT_MUTED).pack(
            anchor="w", padx=20
        )
        return lbl

    def refresh(self):
        overview = BorrowController.get_admin_overview()
        pending = overview["pending_members"] + overview["book_requests"] + overview["profile_requests"]
        self.lbl_tot.configure(text=str(overview["titles"]))
        self.lbl_act.configure(text=str(overview["active_borrows"]))
        self.lbl_members.configure(text=str(overview["members"]))
        self.lbl_pending.configure(text=str(pending))

        overdue = overview["overdue"]
        if overdue:
            self.alert_icon.configure(text="!", text_color=APPLE_RED)
            self.alert_text.configure(
                text=f"{overdue} gecikmiş ödünç kaydı ilgilenmenizi bekliyor.", text_color=APPLE_RED
            )
        else:
            self.alert_icon.configure(text="✓", text_color=APPLE_GREEN)
            self.alert_text.configure(
                text=f"Dolaşım düzenli • toplam {overview['copies']} fiziksel kopya yönetiliyor.",
                text_color=APPLE_GREEN,
            )

        for child in self.activity_list.winfo_children():
            child.destroy()
        activities = BorrowController.get_recent_activity()
        if not activities:
            ctk.CTkLabel(
                self.activity_list,
                text="Henüz kaydedilmiş bir sistem hareketi yok.",
                text_color=APPLE_TEXT_MUTED,
            ).pack(anchor="w", padx=4, pady=12)
            return
        icons = {"BORROW": "↗", "RETURN": "↙", "CREATE": "+", "UPDATE": "✎", "ARCHIVE": "−"}
        for action, description, action_date in activities:
            row = ctk.CTkFrame(self.activity_list, fg_color=GLASS_MUTED, corner_radius=10, height=42)
            row.pack(fill="x", pady=3)
            row.pack_propagate(False)
            ctk.CTkLabel(
                row,
                text=icons.get(action, "•"),
                width=38,
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color=ACCENT,
            ).pack(side="left", padx=(8, 2))
            ctk.CTkLabel(row, text=description, anchor="w").pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(row, text=str(action_date), text_color=APPLE_TEXT_MUTED).pack(side="right", padx=14)


class AdminBooksView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=40, pady=(40, 20))
        ctk.CTkLabel(top, text="📚 Kitap Envanteri", font=ctk.CTkFont(size=32, weight="bold")).pack(
            side="left"
        )
        AnimatedButton(top, text="+ Yeni Kitap", command=self.manual_add).pack(side="right", padx=(8, 0))
        AnimatedButton(
            top,
            text="Arşivle",
            fg_color=APPLE_RED,
            hover_color=("#B52F46", "#E05269"),
            command=self.archive_selected,
        ).pack(side="right", padx=(8, 0))
        AnimatedButton(
            top, text="Düzenle", fg_color=GLASS_MUTED, text_color=APPLE_TEXT, command=self.edit_selected
        ).pack(side="right", padx=(8, 0))
        self.search_entry = ctk.CTkEntry(
            top,
            placeholder_text="Başlık, yazar, ISBN ara…",
            width=240,
            height=38,
            fg_color=INPUT,
            border_color=GLASS_BORDER,
        )
        self.search_entry.pack(side="right", padx=(0, 8))
        self.search_entry.bind("<KeyRelease>", lambda _event: self.refresh())

        # Table
        self.t_frame = GlassFrame(self)
        self.t_frame.pack(fill="both", expand=True, padx=40, pady=(0, 40))

        apply_treeview_style()

        self.tree = ttk.Treeview(
            self.t_frame,
            columns=("id", "title", "author", "isbn", "cat", "year", "tot", "avl"),
            show="headings",
        )
        heads = ["ID", "Başlık", "Yazar", "ISBN", "Kategori", "Yıl", "Toplam", "Mevcut"]
        for c, h in zip(self.tree["columns"], heads, strict=True):
            self.tree.heading(c, text=h)
        self.tree.column("id", width=40)
        self.tree.pack(fill="both", expand=True, padx=20, pady=20)
        self.tree.bind("<Double-1>", self.on_double)

        ctk.CTkLabel(self, text="* Düzenlemek için kitaba çift tıklayın", text_color=APPLE_TEXT_MUTED).pack(
            pady=10
        )
        self.refresh()

    def refresh(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for b in BookController.get_all_books(self.search_entry.get()):
            # Description and cover URL are retained as hidden values for editing.
            self.tree.insert("", "end", values=(b[0], b[1], b[2], b[3], b[4], b[5], b[8], b[9], b[6], b[7]))

    def on_double(self, e):
        self.edit_selected()

    def edit_selected(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Kitap seçin", "Düzenlemek için tablodan bir kitap seçin.")
            return
        EditBookModal(self, self.tree.item(selection, "values"), self.refresh)

    def archive_selected(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Kitap seçin", "Arşivlemek için tablodan bir kitap seçin.")
            return
        values = self.tree.item(selection, "values")
        if not messagebox.askyesno(
            "Kitabı arşivle", f"'{values[1]}' katalogdan kaldırılsın mı? Geçmiş kayıtları korunacak."
        ):
            return
        success, result_message = BookController.delete_book(values[0])
        if success:
            self.refresh()
            messagebox.showinfo("Başarılı", result_message)
        else:
            messagebox.showerror("Arşivlenemedi", result_message)

    def manual_add(self):
        vals = ["", "", "", "", "Genel", str(datetime.date.today().year), "3", "3", "", ""]
        EditBookModal(self, vals, self.refresh, is_new=True)


class EditBookModal(ctk.CTkToplevel):
    def __init__(self, parent, vals, on_complete, is_new=False):
        super().__init__(parent)
        self.title("✏️ Yeni Kitap" if is_new else "✏️ Kitap Düzenle")
        self.geometry("480x790")
        self.configure(fg_color=APPLE_PANEL)
        self.on_complete = on_complete
        self.is_new = is_new
        self.bid = vals[0] if not is_new else None
        self.vals = vals
        self.transient(parent.winfo_toplevel())
        self.grab_set()

        ctk.CTkLabel(
            self,
            text="Yeni Kitap Ekle" if is_new else "Kitap Detayları",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).pack(pady=20)

        self.ents = {}
        for idx, pl in enumerate(["Başlık", "Yazar", "ISBN", "Kategori", "Yıl"]):
            e = ctk.CTkEntry(self, placeholder_text=pl, width=350, height=40)
            e.insert(0, vals[idx + 1])
            e.pack(pady=10)
            self.ents[pl] = e

        self.tot = ctk.CTkEntry(self, placeholder_text="Toplam Kopya Sayısı", width=350, height=40)
        self.tot.insert(0, vals[6])
        self.tot.pack(pady=10)

        self.cover = ctk.CTkEntry(self, placeholder_text="Kapak URL'si (isteğe bağlı)", width=350, height=40)
        self.cover.insert(0, vals[9] if len(vals) > 9 and str(vals[9]) != "None" else "")
        self.cover.pack(pady=10)

        ctk.CTkLabel(self, text="Kitap Özeti (Description)").pack(anchor="w", padx=50)
        self.desc_txt = ctk.CTkTextbox(self, width=350, height=80)
        self.desc_txt.insert("0.0", str(vals[8]) if len(vals) > 8 and str(vals[8]) != "None" else "")
        self.desc_txt.pack(pady=5)

        AnimatedButton(
            self,
            text="✨ İnternetten Özet Çek",
            width=350,
            height=35,
            fg_color=APPLE_ORANGE,
            hover_color="#cc7a00",
            command=self.auto_desc,
        ).pack(pady=5)
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=65, pady=15)
        AnimatedButton(actions, text="Kaydet", height=45, command=self.save).pack(
            side="left", fill="x", expand=True
        )
        if not self.is_new:
            AnimatedButton(
                actions,
                text="Arşivle",
                width=100,
                height=45,
                fg_color=APPLE_RED,
                hover_color=("#B52F46", "#E05269"),
                command=self.archive,
            ).pack(side="left", padx=(10, 0))

    def auto_desc(self):
        t = self.ents["Başlık"].get()
        if not t:
            return
        self.desc_txt.delete("0.0", "end")
        self.desc_txt.insert("0.0", "Aranıyor...")
        self.update()

        def _fetch():
            try:
                r = requests.get(
                    "https://openlibrary.org/search.json",
                    params={"q": t, "limit": 1},
                    timeout=5,
                )
                r.raise_for_status()
                docs = r.json().get("docs", [])
                key = docs[0].get("key") if docs else None
                if key:
                    r2 = requests.get(f"https://openlibrary.org{key}.json", timeout=5)
                    r2.raise_for_status()
                    desc = r2.json().get("description", "Bu kitap için özet bulunamadı.")
                    if isinstance(desc, dict):
                        desc = desc.get("value", "")
                    self.after(
                        0, lambda d=desc: (self.desc_txt.delete("0.0", "end"), self.desc_txt.insert("0.0", d))
                    )
                else:
                    self.after(
                        0,
                        lambda: (
                            self.desc_txt.delete("0.0", "end"),
                            self.desc_txt.insert("0.0", "Sonuç bulunamadı."),
                        ),
                    )
            except requests.RequestException:
                self.after(
                    0,
                    lambda: (self.desc_txt.delete("0.0", "end"), self.desc_txt.insert("0.0", "Hata oluştu.")),
                )

        threading.Thread(target=_fetch, daemon=True).start()

    def save(self):
        desc = self.desc_txt.get("0.0", "end").strip()
        args = (
            self.ents["Başlık"].get(),
            self.ents["Yazar"].get(),
            self.ents["ISBN"].get(),
            self.ents["Kategori"].get(),
            self.ents["Yıl"].get(),
            desc,
            self.cover.get(),
            self.tot.get(),
        )
        if self.is_new:
            success, message = BookController.add_book(*args)
        else:
            success, message = BookController.update_book(self.bid, *args)
        if not success:
            messagebox.showerror("Kitap kaydedilemedi", message, parent=self)
            return
        self.on_complete()
        self.destroy()
        messagebox.showinfo("Başarılı", message)

    def archive(self):
        if not messagebox.askyesno(
            "Kitabı arşivle",
            "Kitap katalogdan kaldırılacak, geçmiş kayıtları korunacak. Devam edilsin mi?",
            parent=self,
        ):
            return
        success, message = BookController.delete_book(self.bid)
        if not success:
            messagebox.showerror("Arşivlenemedi", message, parent=self)
            return
        self.on_complete()
        self.destroy()
        messagebox.showinfo("Başarılı", message)


class AdminApprovalsView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        ctk.CTkLabel(self, text="✅ Bekleyen Onaylar", font=ctk.CTkFont(size=32, weight="bold")).pack(
            anchor="w", padx=40, pady=(40, 20)
        )
        self.t_frame = GlassFrame(self)
        self.t_frame.pack(fill="both", expand=True, padx=40, pady=(0, 12))

        apply_treeview_style()
        self.tree = ttk.Treeview(self.t_frame, columns=("id", "n", "e", "p", "d"), show="headings")
        for c, h in zip(self.tree["columns"], ["ID", "Ad Soyad", "E-posta", "Telefon", "Tarih"], strict=True):
            self.tree.heading(c, text=h)
        self.tree.pack(fill="both", expand=True, padx=20, pady=20)
        self.tree.bind("<Double-1>", self.on_double)
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=40, pady=(0, 28))
        ctk.CTkLabel(
            footer, text="Yeni üyeleri doğrulayıp sisteme kabul edin.", text_color=APPLE_TEXT_MUTED
        ).pack(side="left")
        AnimatedButton(footer, text="Seçili Üyeyi Onayla", command=self.approve_selected).pack(side="right")
        self.refresh()

    def refresh(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for m in MemberController.get_pending_members():
            self.tree.insert("", "end", values=m)

    def on_double(self, e):
        self.approve_selected()

    def approve_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Üye seçin", "Onaylamak için bekleyen bir üyeyi seçin.")
            return
        if messagebox.askyesno("Onayla", "Bu hesabı aktifleştirmek istiyor musunuz?"):
            success, message = MemberController.approve_member(self.tree.item(sel, "values")[0])
            if success:
                self.refresh()
            else:
                messagebox.showerror("Onaylanamadı", message)


class AdminMembersView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=40, pady=(40, 20))
        ctk.CTkLabel(top, text="👥 Üyeler (Onaylı)", font=ctk.CTkFont(size=32, weight="bold")).pack(
            side="left"
        )
        AnimatedButton(top, text="+ Manuel Üye Ekle", command=self.manual_add).pack(side="right")
        AnimatedButton(
            top,
            text="Seçili Üyeyi Arşivle",
            fg_color=APPLE_RED,
            hover_color=("#B52F46", "#E05269"),
            command=self.archive_selected,
        ).pack(side="right", padx=8)
        self.search_entry = ctk.CTkEntry(
            top,
            placeholder_text="Ad veya e-posta ara…",
            width=220,
            height=38,
            fg_color=INPUT,
            border_color=GLASS_BORDER,
        )
        self.search_entry.pack(side="right", padx=(0, 4))
        self.search_entry.bind("<KeyRelease>", lambda _event: self.refresh())

        self.t_frame = GlassFrame(self)
        self.t_frame.pack(fill="both", expand=True, padx=40, pady=(0, 40))
        apply_treeview_style()
        self.tree = ttk.Treeview(self.t_frame, columns=("id", "n", "e", "p", "d"), show="headings")
        for c, h in zip(self.tree["columns"], ["ID", "Ad Soyad", "E-posta", "Telefon", "Tarih"], strict=True):
            self.tree.heading(c, text=h)
        self.tree.pack(fill="both", expand=True, padx=20, pady=20)
        self.tree.bind("<Double-1>", self.on_double)
        self.refresh()

    def refresh(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for m in MemberController.get_all_members(self.search_entry.get()):
            self.tree.insert("", "end", values=m)

    def on_double(self, e):
        self.archive_selected()

    def archive_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Üye seçin", "Arşivlemek için tablodan bir üye seçin.")
            return
        if messagebox.askyesno(
            "Sil",
            "Bu üyeyi arşivlemek istediğinize emin misiniz? Ödünç geçmişi korunacaktır.",
        ):
            success, msg = MemberController.delete_member(self.tree.item(sel, "values")[0])
            if success:
                self.refresh()
            else:
                messagebox.showerror("Hata", msg)

    def manual_add(self):
        AddMemberModal(self.winfo_toplevel(), self.refresh)


class AddMemberModal(ctk.CTkToplevel):
    def __init__(self, parent, on_complete):
        super().__init__(parent)
        self.title("👤 Manuel Üye Ekle")
        self.geometry("450x500")
        self.configure(fg_color=APPLE_PANEL)
        self.on_complete = on_complete
        self.grab_set()

        ctk.CTkLabel(self, text="Yeni Üye Bilgileri", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=20)
        self.ents = {}
        for pl in ["Ad Soyad", "E-posta", "Telefon", "Şifre"]:
            e = ctk.CTkEntry(self, placeholder_text=pl, width=350, height=40)
            if pl == "Şifre":
                e.configure(show="●")
            e.pack(pady=10)
            self.ents[pl] = e

        AnimatedButton(self, text="Ekle ve Aktifleştir", width=350, height=45, command=self.save).pack(
            pady=20
        )

    def save(self):
        succ, msg = MemberController.add_member(
            self.ents["Ad Soyad"].get(),
            self.ents["E-posta"].get(),
            self.ents["Telefon"].get(),
            self.ents["Şifre"].get(),
            approved=True,
            must_change_password=True,
        )
        if succ:
            self.on_complete()
            self.destroy()
            messagebox.showinfo(
                "Başarılı", "Üye aktifleştirildi. İlk girişte şifresini değiştirmesi istenecek."
            )
        else:
            messagebox.showerror("Hata", msg)


class AdminBorrowsView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        ctk.CTkLabel(self, text="⏳ Tüm Ödünç Geçmişi", font=ctk.CTkFont(size=32, weight="bold")).pack(
            anchor="w", padx=40, pady=(40, 20)
        )
        self.t_frame = GlassFrame(self)
        self.t_frame.pack(fill="both", expand=True, padx=40, pady=(0, 12))

        apply_treeview_style()
        self.tree = ttk.Treeview(
            self.t_frame, columns=("id", "b", "m", "bd", "rd", "ad", "f"), show="headings"
        )
        for c, h in zip(
            self.tree["columns"],
            ["ID", "Kitap", "Üye", "Veriliş Tarihi", "Son Teslim", "Durum", "Ceza"],
            strict=True,
        ):
            self.tree.heading(c, text=h)
        self.tree.pack(fill="both", expand=True, padx=20, pady=20)
        self.tree.bind("<Double-1>", self.on_double)
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=40, pady=(0, 28))
        ctk.CTkLabel(
            footer,
            text="Aktif bir kaydı seçerek manuel iade işlemini tamamlayabilirsiniz.",
            text_color=APPLE_TEXT_MUTED,
        ).pack(side="left")
        AnimatedButton(footer, text="Seçili Kaydı İade Al", command=self.return_selected).pack(side="right")
        self.refresh()

    def refresh(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for b in BorrowController.get_all_borrows():
            br_id, title, member, b_date, r_date, act_date, fee = b
            status = "✅ İade Edildi" if act_date and str(act_date) != "None" else "⏳ Kullanıcıda"
            self.tree.insert("", "end", values=(br_id, title, member, b_date, r_date, status, fee))

    def on_double(self, e):
        self.return_selected()

    def return_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Kayıt seçin", "İade almak için aktif bir ödünç kaydı seçin.")
            return
        values = self.tree.item(sel, "values")
        if values[5] != "⏳ Kullanıcıda":
            messagebox.showinfo("İade tamamlanmış", "Bu kayıt daha önce iade edilmiş.")
            return
        if messagebox.askyesno("İade", "Bu kitabı manuel olarak iade almak istiyor musunuz?"):
            success, result_message = BorrowController.return_book(values[0])
            if success:
                self.refresh()
                messagebox.showinfo("Başarılı", result_message)
            else:
                messagebox.showerror("İade alınamadı", result_message)


class AdminOpenLibraryView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        ctk.CTkLabel(self, text="🌐 İnternetten Kitap Ekle", font=ctk.CTkFont(size=32, weight="bold")).pack(
            anchor="w", padx=40, pady=(40, 20)
        )

        self.top = GlassFrame(self, height=100)
        self.top.pack(fill="x", padx=40, pady=(0, 20))
        self.top.pack_propagate(False)

        self.ent = ctk.CTkEntry(
            self.top, placeholder_text="🔍 Kitap Adı, ISBN veya Yazar (OpenLibrary)...", width=500, height=45
        )
        self.ent.pack(side="left", padx=20, pady=20)
        AnimatedButton(self.top, text="Bul", width=100, height=45, command=self.search).pack(side="left")
        self.status = ctk.CTkLabel(self.top, text="", text_color=APPLE_TEXT_MUTED)
        self.status.pack(side="left", padx=20)

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=40)

    def search(self):
        q = self.ent.get()
        if not q:
            return
        self.status.configure(text="Aranıyor...")
        self.update()
        for w in self.scroll.winfo_children():
            w.destroy()

        def _do_search():
            try:
                r = requests.get(
                    "https://openlibrary.org/search.json",
                    params={"q": q, "limit": 10},
                    timeout=10,
                )
                r.raise_for_status()
                docs = r.json().get("docs", [])
                self.after(0, self._show_results, docs)
            except requests.RequestException:
                self.after(0, lambda: self.status.configure(text="❌ Hata oluştu."))

        threading.Thread(target=_do_search, daemon=True).start()

    def _show_results(self, docs):
        self.status.configure(text=f"✅ {len(docs)} sonuç bulundu.")
        rendered = 0
        for d in docs:
            t = d.get("title", "Bilinmiyor")
            authors = d.get("author_name") or ["Bilinmiyor"]
            a = authors[0]
            selected_isbn = first_valid_isbn(d.get("isbn"))
            if not selected_isbn:
                continue
            isbn = selected_isbn
            subjects = d.get("subject") or ["Genel"]
            sub = subjects[0]
            y = d.get("first_publish_year") or datetime.date.today().year

            c = GlassFrame(self.scroll, height=100)
            c.pack(fill="x", pady=10)
            c.pack_propagate(False)

            f_left = ctk.CTkFrame(c, fg_color="transparent")
            f_left.pack(side="left", padx=20, pady=10)
            ctk.CTkLabel(f_left, text=f"📖 {t[:60]}", font=ctk.CTkFont(size=18, weight="bold")).pack(
                anchor="w"
            )
            ctk.CTkLabel(
                f_left, text=f"👤 {a} | 🏷️ {sub} | 📅 {y} | ISBN: {isbn}", text_color=APPLE_TEXT_MUTED
            ).pack(anchor="w")

            f_right = ctk.CTkFrame(c, fg_color="transparent")
            f_right.pack(side="right", padx=20, pady=10)
            ctk.CTkLabel(f_right, text="Adet:").pack(side="left", padx=5)
            qty = ctk.CTkEntry(f_right, width=50)
            qty.insert(0, "3")
            qty.pack(side="left", padx=10)
            AnimatedButton(
                f_right,
                text="Ekle",
                width=80,
                command=lambda title=t, auth=a, i=isbn, s=sub, yr=y, q_ent=qty: self.add_book(
                    title, auth, i, s, yr, q_ent
                ),
            ).pack(side="left")
            rendered += 1

        if rendered == 0:
            self.status.configure(text="ISBN bilgisi olan sonuç bulunamadı.")
            ctk.CTkLabel(
                self.scroll,
                text="Farklı bir kitap adı, yazar veya ISBN ile yeniden deneyin.",
                text_color=APPLE_TEXT_MUTED,
            ).pack(pady=40)

    def add_book(self, t, a, i, s, y, q_ent):
        try:
            cover_url = f"https://covers.openlibrary.org/b/isbn/{i}-L.jpg"
            success, msg = BookController.add_book(t, a, i, s, y, "", cover_url, int(q_ent.get()))
            if success:
                messagebox.showinfo("Başarılı", f"{t} başarıyla eklendi!")
            else:
                messagebox.showerror("Hata", msg)
        except ValueError:
            messagebox.showerror("Hata", "Adet hatalı.")


class AdminRequestsView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        ctk.CTkLabel(self, text="💡 Eklenmesi İstenenler", font=ctk.CTkFont(size=32, weight="bold")).pack(
            anchor="w", padx=40, pady=(40, 20)
        )

        self.t_frame = GlassFrame(self)
        self.t_frame.pack(fill="both", expand=True, padx=40, pady=(0, 12))

        apply_treeview_style()
        self.tree = ttk.Treeview(
            self.t_frame, columns=("id", "mid", "mem", "tit", "aut", "isbn", "date", "url"), show="headings"
        )
        for c, h in zip(
            self.tree["columns"],
            ["ID", "Üye ID", "İsteyen Üye", "Kitap Başlığı", "Yazar", "ISBN", "Tarih", "URL"],
            strict=True,
        ):
            self.tree.heading(c, text=h)
        self.tree.column("url", width=0, stretch=False)
        self.tree.column("mid", width=0, stretch=False)
        self.tree.pack(fill="both", expand=True, padx=20, pady=20)
        self.tree.bind("<Double-1>", self.on_double)

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=40, pady=(0, 28))
        ctk.CTkLabel(
            footer,
            text="İsteği kataloğa ekleyebilir veya üyeye ret bildirimi gönderebilirsiniz.",
            text_color=APPLE_TEXT_MUTED,
        ).pack(side="left")
        AnimatedButton(footer, text="Seçili İsteği İşle", command=self.process_selected).pack(side="right")
        self.refresh()

    def refresh(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for r in RequestController.get_all_requests():
            self.tree.insert("", "end", values=r)

    def on_double(self, e):
        self.process_selected()

    def process_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("İstek seçin", "İşlemek için tablodan bir kitap isteği seçin.")
            return
        vals = self.tree.item(sel, "values")
        req_id, member_id, member_name, title, author, isbn, date, url = vals

        msg = f"{member_name} adlı üye '{title}' kitabını istiyor.\nKütüphaneye eklensin mi?"
        if messagebox.askyesno("Kitap İsteği", msg):
            success, m = BookController.add_book(title, author, isbn, "Genel", 2024, "", url, 3)
            if success:
                messagebox.showinfo("Başarılı", "Kitap kütüphaneye eklendi!")
                RequestController.delete_request(req_id)
                NotificationController.add_notification(
                    member_id, f"🎉 İstediğiniz '{title}' kitabı onaylandı ve kütüphaneye eklendi!"
                )
                self.refresh()
            else:
                messagebox.showerror("Hata", m)
        else:
            if messagebox.askyesno("İsteği Sil", "Bu isteği reddedip listeden silmek ister misiniz?"):
                RequestController.delete_request(req_id)
                NotificationController.add_notification(
                    member_id, f"❌ '{title}' kitabı isteğiniz yönetici tarafından reddedildi."
                )
                self.refresh()


class AdminProfileRequestsView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        ctk.CTkLabel(
            self, text="📝 Profil Değişiklik Talepleri", font=ctk.CTkFont(size=32, weight="bold")
        ).pack(anchor="w", padx=40, pady=(40, 20))

        self.t_frame = GlassFrame(self)
        self.t_frame.pack(fill="both", expand=True, padx=40, pady=(0, 12))

        apply_treeview_style()
        self.tree = ttk.Treeview(
            self.t_frame, columns=("id", "mid", "mem", "nn", "ne", "date"), show="headings"
        )
        for c, h in zip(
            self.tree["columns"],
            ["ID", "Üye ID", "Mevcut Üye Adı", "Yeni İsim", "Yeni E-posta", "Tarih"],
            strict=True,
        ):
            self.tree.heading(c, text=h)
        self.tree.column("mid", width=0, stretch=False)
        self.tree.pack(fill="both", expand=True, padx=20, pady=20)
        self.tree.bind("<Double-1>", self.on_double)

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=40, pady=(0, 28))
        ctk.CTkLabel(
            footer,
            text="Profil değişikliklerini inceleyip üyeye sonuç bildirimi gönderin.",
            text_color=APPLE_TEXT_MUTED,
        ).pack(side="left")
        AnimatedButton(footer, text="Seçili Talebi İncele", command=self.process_selected).pack(side="right")
        self.refresh()

    def refresh(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        from controllers.library import ProfileRequestController

        for r in ProfileRequestController.get_pending_requests():
            self.tree.insert("", "end", values=r)

    def on_double(self, e):
        self.process_selected()

    def process_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Talep seçin", "İncelemek için tablodan bir profil talebi seçin.")
            return
        vals = self.tree.item(sel, "values")
        req_id, member_id, member_name, new_name, new_email, date = vals

        msg = f"{member_name} adlı üye bilgilerini şunlarla değiştirmek istiyor:\n\nYeni İsim: {new_name}\nYeni E-posta: {new_email}\n\nOnaylıyor musunuz?"
        from controllers.library import NotificationController, ProfileRequestController

        if messagebox.askyesno("Profil Talebi", msg):
            success, result_message = ProfileRequestController.approve_request(
                req_id, member_id, new_name, new_email
            )
            if success:
                NotificationController.add_notification(
                    member_id, "🎉 Profil bilgileriniz başarıyla güncellendi."
                )
                self.refresh()
                messagebox.showinfo("Başarılı", result_message)
            else:
                messagebox.showerror("Güncellenemedi", result_message)
        else:
            if messagebox.askyesno("Talebi Reddet", "Bu talebi reddedip silmek ister misiniz?"):
                ProfileRequestController.reject_request(req_id)
                NotificationController.add_notification(
                    member_id, "❌ Profil güncelleme talebiniz reddedildi."
                )
                self.refresh()


class AdminProfileView(ctk.CTkFrame):
    def __init__(self, master, admin_user, on_update):
        super().__init__(master, fg_color="transparent")
        self.admin_user = admin_user
        self.on_update = on_update

        ctk.CTkLabel(self, text="👤 Yönetici Profili", font=ctk.CTkFont(size=32, weight="bold")).pack(
            anchor="w", padx=40, pady=(40, 20)
        )

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=40)

        f1 = GlassFrame(scroll)
        f1.pack(fill="x", pady=10)
        ctk.CTkLabel(f1, text="Genel Bilgiler", font=ctk.CTkFont(size=18, weight="bold")).pack(
            anchor="w", padx=20, pady=(20, 10)
        )

        self.e_user = ctk.CTkEntry(f1, placeholder_text="Kullanıcı Adı", width=300, height=36)
        self.e_user.insert(0, admin_user.get("username", ""))
        self.e_user.pack(anchor="w", padx=20, pady=5)

        self.e_name = ctk.CTkEntry(f1, placeholder_text="Ad Soyad", width=300, height=36)
        self.e_name.insert(0, admin_user.get("name", ""))
        self.e_name.pack(anchor="w", padx=20, pady=5)

        self.e_email = ctk.CTkEntry(f1, placeholder_text="E-posta", width=300, height=36)
        self.e_email.insert(0, admin_user.get("email", ""))
        self.e_email.pack(anchor="w", padx=20, pady=5)

        AnimatedButton(f1, text="Bilgileri Kaydet", width=300, command=self.save_info).pack(
            anchor="w", padx=20, pady=15
        )

        f2 = GlassFrame(scroll)
        f2.pack(fill="x", pady=20)
        ctk.CTkLabel(f2, text="Şifre Değiştir", font=ctk.CTkFont(size=18, weight="bold")).pack(
            anchor="w", padx=20, pady=(20, 10)
        )

        self.e_old_pw = ctk.CTkEntry(f2, placeholder_text="Mevcut Şifre", show="●", width=300, height=36)
        self.e_old_pw.pack(anchor="w", padx=20, pady=5)
        self.e_new_pw1 = ctk.CTkEntry(
            f2, placeholder_text="Yeni Şifre (En az 8 karakter)", show="●", width=300, height=36
        )
        self.e_new_pw1.pack(anchor="w", padx=20, pady=5)
        self.e_new_pw2 = ctk.CTkEntry(
            f2, placeholder_text="Yeni Şifre (Tekrar)", show="●", width=300, height=36
        )
        self.e_new_pw2.pack(anchor="w", padx=20, pady=5)

        self.chk = ctk.CTkCheckBox(f2, text="Şifreleri Göster", command=self.toggle)
        self.chk.pack(anchor="w", padx=20, pady=5)

        AnimatedButton(f2, text="Şifreyi Değiştir", width=300, command=self.save_pw).pack(
            anchor="w", padx=20, pady=15
        )

    def toggle(self):
        s = "" if self.chk.get() == 1 else "●"
        self.e_old_pw.configure(show=s)
        self.e_new_pw1.configure(show=s)
        self.e_new_pw2.configure(show=s)

    def save_info(self):
        u = self.e_user.get().strip()
        n = self.e_name.get().strip()
        e = self.e_email.get().strip()
        if not u or not n or not e:
            messagebox.showerror("Hata", "Tüm alanları doldurun.")
            return
        succ, msg = AuthController.update_admin_profile(self.admin_user["id"], u, n, e)
        if succ:
            self.on_update({"username": u, "name": n, "email": e})
            messagebox.showinfo("Başarılı", msg)
        else:
            messagebox.showerror("Hata", msg)

    def save_pw(self):
        o = self.e_old_pw.get()
        n1 = self.e_new_pw1.get()
        n2 = self.e_new_pw2.get()
        if not o or not n1 or not n2:
            messagebox.showerror("Hata", "Tüm alanları doldurun.")
            return
        if n1 != n2:
            messagebox.showerror("Hata", "Yeni şifreler eşleşmiyor.")
            return
        succ, msg = AuthController.change_admin_password(self.admin_user["id"], o, n1)
        if succ:
            messagebox.showinfo("Başarılı", msg)
            self.e_old_pw.delete(0, "end")
            self.e_new_pw1.delete(0, "end")
            self.e_new_pw2.delete(0, "end")
        else:
            messagebox.showerror("Hata", msg)


class AdminSettingsView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        ctk.CTkLabel(self, text="⚙️ Ayarlar", font=ctk.CTkFont(size=32, weight="bold")).pack(
            anchor="w", padx=40, pady=(40, 20)
        )

        f = GlassFrame(self, height=200)
        f.pack(fill="x", padx=40, pady=(0, 16))
        f.pack_propagate(False)

        ctk.CTkLabel(f, text="Görünüm Modu", font=ctk.CTkFont(size=18, weight="bold")).pack(
            anchor="w", padx=20, pady=(20, 10)
        )
        self.mode_var = ctk.StringVar(value=ctk.get_appearance_mode())

        ctk.CTkRadioButton(
            f, text="Karanlık Mod (Dark)", variable=self.mode_var, value="Dark", command=self.change_mode
        ).pack(anchor="w", padx=20, pady=10)
        ctk.CTkRadioButton(
            f, text="Aydınlık Mod (Light)", variable=self.mode_var, value="Light", command=self.change_mode
        ).pack(anchor="w", padx=20, pady=10)

        maintenance = GlassFrame(self)
        maintenance.pack(fill="x", padx=40, pady=(0, 20))
        ctk.CTkLabel(maintenance, text="Veri Bakımı", font=ctk.CTkFont(size=18, weight="bold")).pack(
            anchor="w", padx=20, pady=(20, 4)
        )
        ctk.CTkLabel(
            maintenance,
            text="Veritabanını denetleyin veya başlangıç kataloğunun kapak ve özet bilgilerini onarın.",
            text_color=APPLE_TEXT_MUTED,
        ).pack(anchor="w", padx=20, pady=(0, 14))
        actions = ctk.CTkFrame(maintenance, fg_color="transparent")
        actions.pack(anchor="w", padx=20, pady=(0, 20))
        AnimatedButton(actions, text="Veritabanını Doğrula", command=self.verify_database).pack(
            side="left", padx=(0, 10)
        )
        AnimatedButton(
            actions,
            text="Katalog Metadatasını Onar",
            fg_color=GLASS_MUTED,
            text_color=APPLE_TEXT,
            command=self.repair_catalog,
        ).pack(side="left")

    def change_mode(self):
        ctk.set_appearance_mode(self.mode_var.get())
        apply_treeview_style()

    def verify_database(self):
        success, result = check_integrity()
        if success:
            messagebox.showinfo("Veritabanı sağlam", "SQLite bütünlük denetimi başarıyla tamamlandı.")
        else:
            messagebox.showerror("Bütünlük sorunu", f"SQLite sonucu: {result}")

    def repair_catalog(self):
        inserted = refresh_catalog_metadata()
        messagebox.showinfo(
            "Katalog hazır",
            f"Kapak ve özet bilgileri doğrulandı. Eksik {inserted} katalog kaydı eklendi.",
        )


class AdminWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("LibSys • Yönetim Stüdyosu")
        self.geometry("1300x850")
        self.minsize(1100, 720)
        ctk.set_appearance_mode("dark")
        self.configure(fg_color=APPLE_BG)
        self.cur = None
        self.admin_user = None
        self.main_shell = None
        self.nav_buttons = {}
        self.show_login()

    def show_login(self):
        if self.cur:
            self.cur.destroy()
            self.cur = None
        if self.main_shell:
            self.main_shell.destroy()
            self.main_shell = None
        self.admin_user = None
        self.cur = AdminLoginView(self, self.show_main)
        self.cur.pack(fill="both", expand=True)

    def update_admin_user(self, new_info):
        self.admin_user.update(new_info)

    def show_main(self, admin_user):
        self.admin_user = admin_user
        if self.cur:
            self.cur.destroy()
        if self.main_shell:
            self.main_shell.destroy()
        m = ctk.CTkFrame(self, fg_color="transparent")
        m.pack(fill="both", expand=True)
        self.main_shell = m

        sb = GlassFrame(m, width=260, corner_radius=0, fg_color=SIDEBAR, border_color=BORDER)
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)

        ctk.CTkLabel(
            sb, text="◈ LIBSYS", font=ctk.CTkFont(size=26, weight="bold"), text_color=APPLE_BLUE
        ).pack(pady=(45, 4))
        ctk.CTkLabel(
            sb, text="YÖNETİM STÜDYOSU", font=ctk.CTkFont(size=10, weight="bold"), text_color=APPLE_TEXT_MUTED
        ).pack(pady=(0, 34))

        self.content = ctk.CTkFrame(m, fg_color="transparent")
        self.content.pack(side="left", fill="both", expand=True)

        def nav(c):
            if self.cur:
                self.cur.destroy()
            if c == AdminProfileView:
                self.cur = c(self.content, self.admin_user, self.update_admin_user)
            else:
                self.cur = c(self.content)
            self.cur.pack(fill="both", expand=True)
            for view_class, button in self.nav_buttons.items():
                is_active = view_class == c
                button.configure(
                    fg_color=GLASS_MUTED if is_active else "transparent",
                    text_color=ACCENT if is_active else APPLE_TEXT,
                )

        ic_cat = get_icon("book")
        ic_home = get_icon("home")
        ic_bell = get_icon("bell")
        ic_prof = get_icon("user")
        ic_set = get_icon("settings")
        ic_search = get_icon("search")
        ic_req = get_icon("star")

        menus = [
            ("Genel Bakış", AdminDashboard, ic_home),
            ("Onay Bekleyenler", AdminApprovalsView, ic_bell),
            ("Kitaplar", AdminBooksView, ic_cat),
            ("İnternetten Ekle", AdminOpenLibraryView, ic_search),
            ("İstenen Kitaplar", AdminRequestsView, ic_req),
            ("Üyeler", AdminMembersView, ic_prof),
            ("Profil İstekleri", AdminProfileRequestsView, ic_bell),
            ("Tüm Geçmiş", AdminBorrowsView, ic_cat),
            ("Profilim", AdminProfileView, ic_prof),
            ("Ayarlar", AdminSettingsView, ic_set),
        ]

        self.nav_buttons = {}
        for text, cls, ic in menus:
            b = ctk.CTkButton(
                sb,
                text=f" {text}",
                image=ic,
                font=ctk.CTkFont(size=14),
                fg_color="transparent",
                text_color=APPLE_TEXT,
                hover_color=GLASS_HOVER,
                anchor="w",
                command=lambda c=cls: nav(c),
                corner_radius=10,
                height=34,
            )
            b.pack(fill="x", padx=15, pady=4)
            self.nav_buttons[cls] = b

        ctk.CTkButton(
            sb,
            text="  Oturumu Kapat",
            image=get_single_icon("logout.png"),
            fg_color="transparent",
            hover_color=GLASS_HOVER,
            text_color=APPLE_RED,
            anchor="w",
            height=38,
            command=self.logout,
        ).pack(side="bottom", fill="x", padx=15, pady=22)

        nav(AdminDashboard)

    def logout(self):
        if messagebox.askyesno("Oturumu kapat", "Yönetici oturumunu kapatmak istiyor musunuz?"):
            self.show_login()
