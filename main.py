from kivy.config import Config
Config.set("graphics", "width", "300")
Config.set("graphics", "height", "570")

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import Image
from kivy.storage.jsonstore import JsonStore
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.properties import DictProperty, StringProperty

from sync import (SyncManager, GAMES, empty_game, new_profile,
                  read_profile, make_event, compute_scores)

# Your Firebase Realtime Database URL (no trailing slash)
FIREBASE_URL = "https://scoreboard-cf838-default-rtdb.europe-west1.firebasedatabase.app"
SYNC_INTERVAL = 30  # seconds


class InputPopup(Popup):
    def __init__(self, callback, title_text, **kwargs):
        super().__init__(**kwargs)
        self.title = title_text
        self.size_hint = (0.8, 0.4)
        self.callback = callback

        layout = BoxLayout(orientation="vertical", spacing=10, padding=10)
        self.textinput = TextInput(multiline=False)
        layout.add_widget(self.textinput)

        button_layout = BoxLayout(size_hint_y=0.4, spacing=10)
        ok_btn = Button(text="OK")
        ok_btn.bind(on_press=self.on_ok)
        cancel_btn = Button(text="Cancel")
        cancel_btn.bind(on_press=self.dismiss)
        button_layout.add_widget(ok_btn)
        button_layout.add_widget(cancel_btn)

        layout.add_widget(button_layout)
        self.content = layout

    def on_ok(self, instance):
        text = self.textinput.text
        self.dismiss()
        self.callback(text)


class InputPopupProfiles(Popup):
    def __init__(self, callback, title_text, options, **kwargs):
        super().__init__(**kwargs)
        self.title = title_text
        self.size_hint = (0.8, 0.4)
        self.callback = callback

        layout = BoxLayout(orientation="vertical", spacing=10, padding=10)
        scroll = ScrollView()
        grid = GridLayout(cols=2, spacing=8, padding=8, size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        for option in options:
            btn = Button(text=option, size_hint_y=None, height=44)
            btn.bind(on_press=self.make_select(option))
            grid.add_widget(btn)
        scroll.add_widget(grid)
        layout.add_widget(scroll)

        cancel_btn = Button(text="Cancel", size_hint_y=None, height=44)
        cancel_btn.bind(on_press=self.dismiss)
        layout.add_widget(cancel_btn)
        self.content = layout

    def make_select(self, option):
        def handler(instance):
            self.dismiss()
            self.callback(option)
        return handler


class ImageButton(ButtonBehavior, Image):
    pass


class MyApp(App):
    current_profile = StringProperty("")
    scores = DictProperty({g: empty_game() for g in GAMES})

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.store = JsonStore("profiles.json")
        self.sync = SyncManager(FIREBASE_URL, self.store,
                                on_profile_updated=self.on_profile_synced)

    def build(self):
        # root widget comes from my.kv (build returns None)
        Clock.schedule_once(lambda dt: self.sync.sync_all(), 1)
        Clock.schedule_interval(lambda dt: self.sync.sync_all(), SYNC_INTERVAL)

    def on_pause(self):
        return True

    def on_resume(self):
        self.sync.sync_all()

    # ---------------- navigation / popups ----------------
    def image_clicked(self, screen_name):
        self.root.current = screen_name

    def show_input(self):
        InputPopup(callback=self.create_profile, title_text="Enter Profile Name").open()

    def show_profiles(self, mode):
        options = sorted(self.store.keys())
        callback = self.load_profile if mode == "load" else self.delete_profile
        InputPopupProfiles(callback=callback, title_text="Pick a Profile",
                           options=options).open()

    def show_message(self, title, text, copyable=False):
        content = BoxLayout(orientation="vertical", padding=10, spacing=10)
        if copyable:
            widget = TextInput(text=text, readonly=True, multiline=False,
                               font_size="24sp", halign="center")
        else:
            widget = Label(text=text, halign="center", valign="middle")
            widget.bind(size=lambda w, s: setattr(w, "text_size", s))
        ok = Button(text="OK", size_hint_y=None, height=44)
        content.add_widget(widget)
        content.add_widget(ok)
        popup = Popup(title=title, content=content, size_hint=(0.8, 0.4))
        ok.bind(on_press=popup.dismiss)
        popup.open()

    # ---------------- profiles ----------------
    def _refresh_scores(self):
        if not self.current_profile or not self.store.exists(self.current_profile):
            self.scores = {g: empty_game() for g in GAMES}
            return
        data = read_profile(self.store, self.current_profile)
        self.scores = compute_scores(data["baseline"], data["events"])

    def load_profile(self, name):
        self.current_profile = name
        self._refresh_scores()
        self.sync.sync_profile(name)  # grab fresh changes if shared + online

    def create_profile(self, name):
        name = name.strip()
        if not name:
            return
        if not self.store.exists(name):
            self.store.put(name, **new_profile())
        self.load_profile(name)

    def delete_profile(self, name):
        # only deletes the local copy; the shared online data stays for the friend
        self.store.delete(name)
        if name == self.current_profile:
            self.current_profile = ""
            self._refresh_scores()

    # player: 0 or 1, sign: +1 or -1
    def change_score(self, game, player, sign):
        if not self.current_profile or not self.store.exists(self.current_profile):
            return
        data = read_profile(self.store, self.current_profile)
        event = make_event(game, player, sign)
        data["events"][event["id"]] = event
        if data["share_code"]:
            data["pending"].append(event["id"])
        self.store.put(self.current_profile, **data)
        self._refresh_scores()
        if data["share_code"]:
            self.sync.sync_profile(self.current_profile)

    # ---------------- sharing ----------------
    def share_current_profile(self):
        if not self.current_profile:
            self.show_message("No profile", "Load a profile first.")
            return
        self.sync.share_profile(
            self.current_profile,
            on_done=lambda code: self.show_message("Share this code", code, copyable=True),
            on_fail=lambda err: self.show_message(
                "Offline?", "Sharing needs an internet\nconnection once."),
        )

    def show_join(self):
        InputPopup(callback=self.join_shared, title_text="Enter Share Code").open()

    def join_shared(self, code):
        self.sync.join_profile(
            code,
            on_done=self.load_profile,
            on_fail=lambda msg: self.show_message("Could not join", str(msg)),
        )

    def sync_now(self):
        self.sync.sync_all()

    def on_profile_synced(self, name):
        if name == self.current_profile:
            self._refresh_scores()


MyApp().run()
# .\kivy_env\Scripts\Activate.ps1 (To activate venv)