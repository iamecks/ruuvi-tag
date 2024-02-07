import logging
import sys
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.core.window import Window
from kivy.clock import Clock
import threading
import asyncio
import pressure_ruvvi_main as pr_main
class LogHandler(logging.Handler):
    """Custom logging handler that updates a GUI with log messages."""

    def __init__(self, update_callback):
        super(LogHandler, self).__init__()
        self.update_callback = update_callback

    def emit(self, record):
        log_message = self.format(record)
        Clock.schedule_once(lambda dt: self.update_callback(log_message), 0)

class LoggerOutput:
    """Custom output stream that updates a GUI with messages."""

    def __init__(self, update_callback):
        self.update_callback = update_callback

    def write(self, message):
        Clock.schedule_once(lambda dt: self.update_callback(message), 0)

    def flush(self):
        pass

class PressureRuvviApp(App):
    """Main application class."""

    def build(self):
        """Set up the GUI."""
        # Set the background color
        Window.clearcolor = (0.02, 0.12, 0.26, 1)  # RGB values for #041E42

        self.layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        self.setup_gui()
        return self.layout

    def setup_gui(self):
        """Create the GUI elements."""
        self.num_devices_input = TextInput(hint_text='Number of devices', multiline=False, size_hint_y=None, height=30)
        self.logging_window_label = Label(text='Logging:', size_hint_y=None, height=20,halign='left', valign='top')
        self.logging_window_label.bind(size=self.logging_window_label.setter('text_size'))
        self.start_button = Button(text='Start', on_press=self.start_pressed, size_hint=(None, None), width=100,height=30)
        self.stop_button = Button(text='Stop', on_press=self.stop_pressed, size_hint=(None, None), width=100, height=30)  # Create a new Stop button
        self.logger_text = TextInput(text='', height=300, multiline=True, background_color=[0.9, 0.9, 0.9, 1])

        # Create BoxLayouts for the buttons
        start_button_layout = BoxLayout(size_hint=(1, None), height=30)
        stop_button_layout = BoxLayout(size_hint=(1, None), height=30)

        # Add the buttons to the BoxLayouts with a Label as a spacer
        start_button_layout.add_widget(self.start_button)
        start_button_layout.add_widget(Label())
        stop_button_layout.add_widget(Label())
        stop_button_layout.add_widget(self.stop_button)

        # Create a new GridLayout for the buttons
        button_layout = GridLayout(cols=2, size_hint_y=None, height=30)
        button_layout.add_widget(start_button_layout)
        button_layout.add_widget(stop_button_layout)

        # Add the widgets to the main layout
        self.layout.add_widget(self.num_devices_input)
        self.layout.add_widget(self.logging_window_label)
        self.layout.add_widget(self.logger_text)
        self.layout.add_widget(button_layout)  # Add the GridLayout to the main layout
        
    def start_pressed(self, instance):
        """Handle the Start button press event."""
        self.start_button.disabled = True
        num_devices = int(self.num_devices_input.text)

        self.logger_text.text += f'Connecting...'

        self.setup_logging_and_output()

        Clock.schedule_once(lambda dt: self.run_pressure_ruvvi_main(pr_main, num_devices), 0)

    def setup_logging_and_output(self):
        """Set up logging and output redirection."""
        self.log_handler = LogHandler(self.update_logger_text)
        logging.basicConfig(level=logging.INFO, handlers=[self.log_handler])

        sys.stdout = LoggerOutput(self.update_logger_text)
        sys.stderr = LoggerOutput(self.update_logger_text)

    def stop_pressed(self, instance):
        """Handle the Stop button press event."""
        if self.data_collection_thread.is_alive():
            # Cancel all running tasks
            for task in asyncio.all_tasks(self.loop):
                task.cancel()
            # Stop the loop and the thread
            self.loop.call_soon_threadsafe(self.loop.stop)
            self.data_collection_thread.join()
            self.logger_text.text += f'\nData collection stopped.\n'
            self.start_button.opacity = 0

    def stop(self, *args):
        """Handle the application close event."""
        self.stop_pressed(None)
        super().stop()  # Call the original stop method to ensure the app is closed properly

    def update_logger_text(self, log_message):
        """Update the logger text input with a new log message."""
        self.logger_text.text += f'\n{log_message}'

    def run_pressure_ruvvi_main(self, pr_main, num_devices):
        """Run pressure_ruvvi_main with the specified number of devices in a separate thread."""
        self.data_collection_thread = threading.Thread(
            target=self.run_pressure_ruvvi_main_thread, args=(pr_main, num_devices)
        )
        self.data_collection_thread.start()

    def run_pressure_ruvvi_main_thread(self, pr_main, num_devices):
        """Use asyncio's event loop in a separate thread."""
        asyncio.set_event_loop(asyncio.new_event_loop())
        self.loop = asyncio.get_event_loop()

        try:
            self.setup_logging_and_output()

            # Run the pressure_ruvvi_main script
            self.loop.run_until_complete(pr_main.ruuvi(num_devices))
        except asyncio.CancelledError:
            pass

if __name__ == '__main__':
    PressureRuvviApp().run()