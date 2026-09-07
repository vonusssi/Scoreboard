"""from kivy.config import Config

Config.set("graphics", "width", "300")
Config.set("graphics", "height", "570")
"""
from kivy.app import App
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import Image
from kivy.storage.jsonstore import JsonStore
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.textinput import TextInput
from kivy.properties import DictProperty
from kivy.uix.label import Label
from kivy.properties import StringProperty
from kivy.properties import NumericProperty
from datetime import date
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
import json 
import os


class InputPopup(Popup):
    def __init__(self, callback, title_text, **kwargs):
        super().__init__(**kwargs)
        self.title = title_text
        self.size_hint = (0.8, 0.4)

        self.callback = callback  # function to call with the input

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
        self.callback(text)  # call the function with the input
        self.dismiss()
class InputPopupProfiles(Popup):
    def __init__(self, callback, title_text, options, **kwargs):
        super().__init__(**kwargs)
        self.title = title_text
        self.size_hint = (0.8, 0.4)

        self.callback = callback  # function to call with the input

        layout = BoxLayout(orientation="vertical", spacing=10, padding=10)
        
        scroll = ScrollView()
        grid = GridLayout(
            cols=2,
            spacing=8,
            padding=8,
            size_hint_y=None,
        )
        grid.bind(minimum_height=grid.setter("height"))
        for option in options:
            btn = Button(text=option,size_hint_y=None,
                height=44,)
            btn.bind(on_press=self.make_select(option))
            grid.add_widget(btn)

        scroll.add_widget(grid)
        layout.add_widget(scroll)

        # Cancel button at the bottom
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
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.store = JsonStore("profiles.json")
    current_profile = StringProperty("")
    scores = DictProperty({
        "ever": [[0,0],["00.00.0000","00.00.0000"],[0,0]],
        "pagan": [[0,0],["00.00.0000","00.00.0000"],[0,0]],
        "wonders": [[0,0],["00.00.0000","00.00.0000"],[0,0]]
    })
    def show_input(self):
        # show popup and handle input
        popup = InputPopup(callback=self.create_profile, title_text="Enter Profile Name")
        popup.open()
    def show_profiles(self, mode):
        json_path = os.path.join(os.path.dirname(__file__), "profiles.json")
        with open(json_path, "r") as f:
            profiles = json.load(f)
        if mode=="load":    
            popup = InputPopupProfiles(callback=self.load_profile, title_text="Pick a Profile",options=profiles)
        elif mode=="delete":
            popup = InputPopupProfiles(callback=self.delete_profile, title_text="Pick a Profile",options=profiles)
        popup.open()

    def image_clicked(self, screen_name):
        self.root.current = screen_name

    def build(self):
            self.store = JsonStore("profiles.json")

    def load_profile(self, name):
        self.current_profile = name
        data = self.store.get(name)
        self.scores= {"ever": list(data["ever"]),
            "pagan": list(data["pagan"]),
            "wonders": list(data["wonders"])
        }
    def delete_profile(self, name):
        self.store.delete(name)
    def create_profile(self, name):

        self.current_profile = name
        if not self.store.exists(name):
            self.store.put(name, ever=[[0,0],["00.00.0000","00.00.0000"],[0,0]], pagan=[[0,0],["00.00.0000","00.00.0000"],[0,0]], wonders=[[0,0],["00.00.0000","00.00.0000"],[0,0]])
        data = self.store.get(name)
        self.scores= {"ever": list(data["ever"]),
            "pagan": list(data["pagan"]),
            "wonders": list(data["wonders"])
        }
    

    """    def add_score_Input_1(self):
        popup=InputPopup(callback=self.change_score, title_text="") 
    def add_score_Input_2(self):
        popup=InputPopup(callback=self.change_score, title_text="") 
    def minus_score_Input_2(self):
        popup=InputPopup(callback=self.change_score, title_text="")    
    def minus_score_Input_2(self):
        popup=InputPopup(callback=self.change_score, title_text="")     """
    #Here Player is either 0 or 1 to give first or second player a score up or down
    #Sign is either + or - 1
    def change_score(self, game, player, sign):
        if self.current_profile=="":
            return 0
        if not self.store.exists(self.current_profile):
            return 0
        data = self.store.get(self.current_profile)

        #Change Score here 
        (data[game])[0][player] += sign
        #Change Date
        data[game][1][player]=date.today().strftime("%d.%m.%Y")
        #Change Streak
        data[game][2][player]+=sign
        data[game][2][(player-1)**2]=0
        
        self.store.put(self.current_profile, **data)
        self.store.put(self.current_profile, **data)
        self.scores[game] = list(data[game])
 

    """
    def get_score(self, game,player):
        if self.current_profile=="":
            return 0
        if not self.store.exists(self.current_profile):
            return 0


        data = self.store.get(self.current_profile)
        self.ever_score1 = (data[game])[player]
        return self.ever_score1
    """



MyApp().run()
#.\kivy_env\Scripts\Activate.ps1 (To activate venv)
"""<MyLayout>:
    Button:
        text: "Press me"
        on_press: app.on_submit()	
        """