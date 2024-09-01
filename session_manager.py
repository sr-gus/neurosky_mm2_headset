from matplotlib import animation
import serial
from datetime import datetime
import time
import threading
import csv
import numpy as np
from scipy.fftpack import fft
from scipy.signal import spectrogram
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
from matplotlib.dates import DateFormatter
from neurosky_interface import NeuroSkyInterface

SAMPLE_RATE = 100  # [Hz]
MAX_LIVE_SAMPLES = 1000
MAX_RECORDED_SAMPLES = 1000
ZERO_THRESHOLD = 1000

class SessionManager:
    def __init__(self, db_manager, device_port):
        self.db_manager = db_manager
        self.device_port = device_port
        self.current_session_id = None
        self.is_collecting = False
        self.interface = None
        self.raw_data = []
        self.zero_count = 0 
        self.collection_thread = None

    def connect_interface(self):
        try:
            self.interface = NeuroSkyInterface(self.device_port)
        except serial.SerialException as e:
            print(f"Error al conectar con el dispositivo NeuroSky: {e}")
            self.interface = None
        except Exception as e:
            print(f"Error inesperado al conectar con el dispositivo NeuroSky: {e}")
            self.interface = None

    def start_new_session(self, user_id):
        self.connect_interface()
        if self.interface is None:
            print("No se pudo iniciar la sesión debido a problemas de conexión con el MindWave.")
            self.end_session()
            return 

        self.current_session_id = self.db_manager.start_session(user_id)
        if self.current_session_id is None:
            print("No se pudo iniciar la sesión en la base de datos.")
            self.end_session()
            return 

        self.is_collecting = True
        self.raw_data = []
        self.zero_count = 0
        self.collect_data()

    def end_session(self):
        self.is_collecting = False
        if self.collection_thread is not None:
            self.collection_thread.join()  

        if self.current_session_id is not None:
            self.db_manager.end_session(self.current_session_id)
            self.current_session_id = None
        if self.interface is not None:
            self.interface.stop()

    def collect_data(self):
        def collect():
            retries = 3
            while self.is_collecting:
                try:
                    raw_value = self.interface.raw_value
                    self.raw_data.append(raw_value)

                    if raw_value == 0:
                        self.zero_count += 1
                    else:
                        self.zero_count = 0

                    if self.zero_count >= ZERO_THRESHOLD:
                        print(f"Se han recibido {self.zero_count} ceros consecutivos. Posible desconexión.")
                        retries -= 1
                        if retries <= 0:
                            print("No se pudo recuperar la conexión después de varios intentos. Finalizando sesión.")
                            self.end_session()
                            break

                    data_point = {
                        'timestamp': time.time(),
                        'raw_value': raw_value,
                    }
                    self.db_manager.save_data(self.current_session_id, data_point)
                    time.sleep(1 / SAMPLE_RATE)

                except serial.SerialException as e:
                    print(f"Error durante la recolección de datos: {e}")
                    retries -= 1
                    if retries <= 0:
                        print("Se superó el número máximo de reintentos. Finalizando sesión.")
                        self.end_session()
                        break
                except Exception as e:
                    print(f"Error inesperado durante la recolección de datos: {e}")
                    retries -= 1
                    if retries <= 0:
                        print("Se superó el número máximo de reintentos. Finalizando sesión.")
                        self.end_session()
                        break

        self.collection_thread = threading.Thread(target=collect)
        self.collection_thread.daemon = True
        self.collection_thread.start()

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

    def plot_frequency_spectrum(self, session_data):
        raw_values = np.array([d['raw_value'] for d in session_data])
        raw_values = raw_values - np.mean(raw_values)
        n = len(raw_values)
        yf = fft(raw_values)
        xf = np.fft.fftfreq(n, 1 / SAMPLE_RATE)

        plt.figure(figsize=(10, 6))
        plt.plot(xf[:n // 2], np.abs(yf[:n // 2]))
        plt.title('Espectro de Frecuencia')
        plt.xlabel('Frecuencia (Hz)')
        plt.ylabel('Amplitud')
        plt.show()

    def plot_spectrogram(self, session_data):
        raw_values = np.array([d['raw_value'] for d in session_data])
        f, t, Sxx = spectrogram(raw_values, SAMPLE_RATE)

        plt.figure(figsize=(10, 6))
        plt.pcolormesh(t, f, 10 * np.log10(Sxx))
        plt.ylabel('Frecuencia [Hz]')
        plt.xlabel('Tiempo [s]')
        plt.title('Espectrograma')
        plt.colorbar(label='Intensidad (dB)')
        plt.show()

    def export_session_to_csv(self, session_data, filename):
        keys = session_data[0].keys()
        with open(filename, 'w', newline='') as output_file:
            dict_writer = csv.DictWriter(output_file, keys)
            dict_writer.writeheader()
            dict_writer.writerows(session_data)