import logging
import sys
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.clock import Clock
import threading
import asyncio
import pressure_ruvvi_main as pr_main


class LogHandler(logging.Handler):
    def __init__(self, update_callback):
        super(LogHandler, self).__init__()
        self.update_callback = update_callback

    def emit(self, record):
        log_message = self.format(record)
        Clock.schedule_once(lambda dt: self.update_callback(log_message), 0)


class LoggerOutput:
    def __init__(self, update_callback):
        self.update_callback = update_callback

    def write(self, message):
        Clock.schedule_once(lambda dt: self.update_callback(message), 0)

    def flush(self):
        pass


class PressureRuvviApp(App):
    def build(self):
        self.layout = BoxLayout(orientation='vertical', spacing=10, padding=10)

        self.num_devices_input = TextInput(hint_text='Number of devices', multiline=False)
        self.start_button = Button(text='Start', on_press=self.start_pressed)
        self.logger_text = TextInput(text='', height=300, multiline=True)

        self.layout.add_widget(self.num_devices_input)
        self.layout.add_widget(self.start_button)
        self.layout.add_widget(self.logger_text)

        return self.layout

    def start_pressed(self, instance):
        self.start_button.disabled = True
        num_devices = int(self.num_devices_input.text)

        self.logger_text.text += f'Connecting...'

        self.log_handler = LogHandler(self.update_logger_text)
        logging.basicConfig(level=logging.INFO, handlers=[self.log_handler])

        sys.stdout = LoggerOutput(self.update_logger_text)
        sys.stderr = LoggerOutput(self.update_logger_text)

        Clock.schedule_once(lambda dt: self.run_pressure_ruvvi_main(pr_main, num_devices), 0)

    def update_logger_text(self, log_message):
        self.logger_text.text += f'\n{log_message}'

    def run_pressure_ruvvi_main(self, pr_main, num_devices):
        # Run pressure_ruvvi_main with the specified number of devices in a separate thread
        self.data_collection_thread = threading.Thread(
            target=self.run_pressure_ruvvi_main_thread, args=(pr_main, num_devices)
        )
        self.data_collection_thread.start()

    def run_pressure_ruvvi_main_thread(self, pr_main, num_devices):
        # Use asyncio's event loop in a separate thread
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()

        try:
            # Redirect logs to the LogHandler
            pr_main.logging.basicConfig(level=pr_main.logging.INFO, handlers=[self.log_handler])

            # Redirect standard output and error
            sys.stdout = LoggerOutput(self.update_logger_text)
            sys.stderr = LoggerOutput(self.update_logger_text)

            # Run the pressure_ruvvi_main script
            loop.run_until_complete(pr_main.ruuvi(num_devices))
        except asyncio.CancelledError:
            pass


if __name__ == '__main__':
    PressureRuvviApp().run()
