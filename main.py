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
        popup = InputPopup(callback=self.load_profile, title_text="Enter Profile Name")
        popup.open()
    def image_clicked(self, screen_name):
        self.root.current = screen_name

    def build(self):
            self.store = JsonStore("profiles.json")

    def load_profile(self, name):
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
