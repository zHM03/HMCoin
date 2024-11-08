import kivy
from kivy.app import App
from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.progressbar import ProgressBar
from kivy.uix.scrollview import ScrollView
from kivy.garden.graph import Graph, LinePlot
from kivy.clock import Clock, mainthread
import requests
import pandas as pd
import threading
from kivy.uix.floatlayout import FloatLayout


class CryptoLabel(Button):
    def __init__(self, coin_name, app, **kwargs):
        super().__init__(**kwargs)
        self.coin_name = coin_name
        self.text = f'{coin_name}: -'
        self.font_size = 20
        self.background_color = (0.1, 0.1, 0.3, 1)
        self.color = (1, 1, 1, 1)
        self.app = app
        self.bind(on_press=self.on_press)

    def on_press(self, instance=None):
        print(f"{self.coin_name} coinine tıklanmış.")
        self.app.show_loading_screen()  # Show loading screen
        threading.Thread(target=self.app.calculate_rsi, args=(self.coin_name,)).start()

    def update_price(self, price):
        self.text = f'{self.coin_name}: ${price:.2f}'


class CoinContainer(BoxLayout):
    def __init__(self, coin_name, app, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.coin_name = coin_name
        self.app = app

        self.graph_layout = BoxLayout(size_hint_y=None, height=300)
        self.rsi_layout = BoxLayout(size_hint_y=None, height=40)

        self.layout = FloatLayout(size_hint_y=None, height=340)

        self.graph_layout.pos_hint = {'top': 0.1}
        self.layout.add_widget(self.graph_layout)
        self.layout.add_widget(self.rsi_layout)

        self.add_widget(self.layout)

        self.graph = None
        self.rsi_label = None

    def update_rsi(self, rsi):
        if self.rsi_label:
            self.rsi_layout.remove_widget(self.rsi_label)

        self.rsi_label = Button(
            text=f'{self.coin_name} RSI= {rsi:.2f}', 
            size_hint=(1, None), 
            height=40, 
            background_color=(0.1, 0.1, 0.3, 1),
            pos_hint={'y': -9} 
        )
        self.rsi_layout.add_widget(self.rsi_label)

    def update_graph(self, prices):
        if self.graph:
            self.graph_layout.clear_widgets()

        self.graph = Graph(
            xlabel='Hours', ylabel='Price (USD)', 
            x_ticks_minor=5, y_ticks_minor=5, 
            xmin=0, ymin=min(prices)-10, ymax=max(prices)+10, 
            x_ticks_major=20,
            size_hint=(1, 1) 
        )

        plot = LinePlot()
        plot.points = [(i, price) for i, price in enumerate(prices)]
        plot.line_color = (1, 0, 0, 1)

        self.graph.add_plot(plot)
        self.graph_layout.add_widget(self.graph)


class CryptoRSIApp(App):
    def build(self):
        self.layout = BoxLayout(orientation='horizontal', padding=10, spacing=10)
        self.coins = ['BTC', 'ETH', 'ETC','FET', 'RENDER']
        self.coin_labels = []

        self.coin_list_layout = BoxLayout(orientation='vertical', size_hint=(0.3, 1), padding=10, spacing=10)
        for coin in self.coins:
            coin_label = CryptoLabel(coin, self)
            self.coin_labels.append(coin_label)
            self.coin_list_layout.add_widget(coin_label)

        self.result_layout = BoxLayout(orientation='vertical', size_hint=(0.7, 1))
        self.result_layout.add_widget(Label(
            text='HMCoin',
            font_size=60,
            font_name='assets/KONSTANTINE.ttf',
            size_hint=(1, 0.1)
        ))

        line = BoxLayout(size_hint=(1, None), height=2)
        with line.canvas.before:
            Color(0.1, 0.1, 0.3, 1)
            self.rect = Rectangle(size=line.size, pos=line.pos)
        self.result_layout.add_widget(line)
        line.bind(size=self.update_rect, pos=self.update_rect)

        self.scroll_view = ScrollView(size_hint=(1, 0.85))
        self.scroll_container = BoxLayout(orientation='vertical', size_hint_y=None)
        self.scroll_container.bind(minimum_height=self.scroll_container.setter('height'))
        self.scroll_view.add_widget(self.scroll_container)
        self.result_layout.add_widget(self.scroll_view)

        self.layout.add_widget(self.coin_list_layout)
        self.layout.add_widget(self.result_layout)

        self.loading_screen = ProgressBar(size_hint=(1, 0.1), max=100, value=0)
        self.result_layout.add_widget(self.loading_screen)
        self.loading_screen.opacity = 0  # Hide loading screen initially

        self.update_prices(0)
        Clock.schedule_interval(self.update_prices, 10)

        return self.layout

    def update_rect(self, instance, value):
        self.rect.size = instance.size
        self.rect.pos = instance.pos

    def update_prices(self, dt):
        for coin_label in self.coin_labels:
            price = self.get_price(coin_label.coin_name)
            if price is not None:
                coin_label.update_price(price)

    def get_price(self, coin):
        url = f'https://min-api.cryptocompare.com/data/price?fsym={coin}&tsyms=USD'
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return data['USD']
        return None

    def calculate_rsi(self, coin):
        url = f'https://min-api.cryptocompare.com/data/histohour?fsym={coin}&tsym=USD&limit=2000&aggregate=4'
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            prices = [entry['close'] for entry in data['Data']]
            df = pd.DataFrame(prices, columns=['price'])
            df['rsi'] = self.calculate_rsi_values(df['price'], 14)
            latest_rsi = df['rsi'].iloc[-1]

            self.create_or_update_container(coin, latest_rsi, prices)
            self.hide_loading_screen()  # Hide loading screen after data is loaded
        else:
            Clock.schedule_once(lambda dt: self.display_error_label())

    @mainthread
    def create_or_update_container(self, coin, latest_rsi, prices):
        self.scroll_container.clear_widgets()

        container = CoinContainer(coin, self)
        self.scroll_container.add_widget(container)

        container.update_rsi(latest_rsi)
        container.update_graph(prices)

    @mainthread
    def display_error_label(self):
        error_label = Button(text='Bir Hata Oluştu.', size_hint=(1, None), height=40, background_color=(0.5, 0.1, 0.1, 1))
        self.scroll_container.add_widget(error_label)
        self.hide_loading_screen()

    @mainthread
    def show_loading_screen(self):
        self.loading_screen.opacity = 1  # Show loading screen
        self.loading_screen.value = 50  # Optionally update the value

    @mainthread
    def hide_loading_screen(self):
        self.loading_screen.opacity = 0  # Hide loading screen

    def calculate_rsi_values(self, data, window=14):
        delta = data.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.ewm(alpha=1/window, min_periods=window).mean()
        avg_loss = loss.ewm(alpha=1/window, min_periods=window).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi


if __name__ == '__main__':
    CryptoRSIApp().run()
