from datetime import datetime
import time
import threading
import csv
from matplotlib import animation
import matplotlib.pyplot as plt
from neurosky_interface import NeuroSkyInterface
from matplotlib.widgets import Slider
from matplotlib.dates import DateFormatter

SAMPLE_RATE          = 100 # [Hz]
MAX_LIVE_SAMPLES     = 1000
MAX_RECORDED_SAMPLES = 1000

class SessionManager:
    def __init__(self, db_manager, device_port):
        self.db_manager = db_manager
        self.interface = NeuroSkyInterface(device_port)
        self.current_session_id = None
        self.is_collecting = False

    def start_new_session(self, user_id):
        self.current_session_id = self.db_manager.start_session(user_id)
        self.is_collecting = True
        self.raw_data = []
        self.collect_data()

    def end_session(self):
        self.is_collecting = False
        self.db_manager.end_session(self.current_session_id)
        self.current_session_id = None
        self.interface.stop()

    def collect_data(self):
        def collect():
            while self.is_collecting:
                self.raw_data.append(self.interface.raw_value)
                data_point = {
                    'timestamp': time.time(),
                    'raw_value': self.interface.raw_value,
                }
                self.db_manager.save_data(self.current_session_id, data_point)
                time.sleep(1/SAMPLE_RATE)

        thread = threading.Thread(target=collect)
        thread.daemon = True
        thread.start()

    def initialize_plot(self): 
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.set_xlim(0, MAX_LIVE_SAMPLES)
        ax.set_ylim(-2048, 2047) 
        ax.set_title('Señal Cruda del EEG en Tiempo Real')
        ax.set_xlabel('Muestras')
        ax.set_ylabel('Amplitud (µV)')
        line, = ax.plot([], [], lw=2, color='red')

        def update(frame):
            if len(self.raw_data) > MAX_LIVE_SAMPLES:
                self.raw_data.pop(0)
            line.set_data(range(len(self.raw_data)), self.raw_data)
            return line,

        ani = animation.FuncAnimation(fig, update, blit=True, interval=10)

        plt.show()

    def plot_session_data(self, session_data):
        raw_values = [d['raw_value'] for d in session_data]
        timestamps = [datetime.fromtimestamp(d['timestamp']) for d in session_data]  
        total_samples = len(raw_values)

        fig, ax = plt.subplots(figsize=(10, 6))
        plt.subplots_adjust(bottom=0.25)

        if total_samples > MAX_RECORDED_SAMPLES:
            raw_values_subset = raw_values[:MAX_RECORDED_SAMPLES]
            timestamps_subset = timestamps[:MAX_RECORDED_SAMPLES]
        else:
            raw_values_subset = raw_values
            timestamps_subset = timestamps

        l, = ax.plot(timestamps_subset, raw_values_subset, label='Señal Cruda')
        ax.set_xlim(timestamps_subset[0], timestamps_subset[-1])
        ax.set_ylim(min(raw_values) - abs(min(raw_values)) / 10, 
                    max(raw_values) + abs(max(raw_values)) / 10) 
        plt.legend()
        plt.title('Datos de la Sesión')
        plt.xlabel('Tiempo')
        plt.ylabel('Valor')

        ax.xaxis.set_major_formatter(DateFormatter('%H:%M:%S'))

        if total_samples > MAX_RECORDED_SAMPLES:
            ax_slider = plt.axes([0.1, 0.1, 0.8, 0.03], facecolor='lightgoldenrodyellow')
            scroll_slider = Slider(ax_slider, 'Scroll', 0, total_samples - MAX_RECORDED_SAMPLES, valinit=0, valstep=1)

            def update(val):
                pos = int(scroll_slider.val)
                raw_values_subset = raw_values[pos:pos + MAX_RECORDED_SAMPLES]
                timestamps_subset = timestamps[pos:pos + MAX_RECORDED_SAMPLES]
                l.set_data(timestamps_subset, raw_values_subset)
                ax.set_xlim(timestamps_subset[0], timestamps_subset[-1])
                fig.canvas.draw_idle()

            scroll_slider.on_changed(update)

        plt.show()

    def export_session_to_csv(self, session_data, filename):
        keys = session_data[0].keys()
        with open(filename, 'w', newline='') as output_file:
            dict_writer = csv.DictWriter(output_file, keys)
            dict_writer.writeheader()
            dict_writer.writerows(session_data)
