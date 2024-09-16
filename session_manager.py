from matplotlib import animation
import serial
from datetime import datetime
import time
import threading
import csv
import numpy as np
from scipy.fft import fft
from scipy.signal import spectrogram
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
from matplotlib.dates import DateFormatter
from neurosky_interface import NeuroSkyInterface

SAMPLE_ATTEMPT_FREQ = 255.0  # [Hz]
MAX_LIVE_SAMPLES = 1000
MAX_RECORDED_SAMPLES = 1000
ZERO_THRESHOLD = 1000
MAX_INTERVAL_MINUTES = 10
BATCH_SIZE = 1000

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
            data_batch = []
            
            while self.is_collecting:
                try:
                    current_time = time.time() 
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
                        'timestamp': current_time, 
                        'raw_value': raw_value,
                    }
                    data_batch.append(data_point)

                    if len(data_batch) >= BATCH_SIZE:
                        self.db_manager.save_data_batch(self.current_session_id, data_batch)
                        data_batch.clear()

                    time.sleep(1 / SAMPLE_ATTEMPT_FREQ)

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
            if data_batch:
                self.db_manager.save_data_batch(self.current_session_id, data_batch)

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

    def calculate_real_sample_rate(self, session_data):
        if len(session_data) < 2:
            return SAMPLE_ATTEMPT_FREQ 
        
        timestamps = np.array([d['timestamp'] for d in session_data])
        time_diffs = np.diff(timestamps)
        
        if np.any(time_diffs <= 0):
            return SAMPLE_ATTEMPT_FREQ 

        real_sample_rate = 1 / np.mean(time_diffs)
        
        if real_sample_rate > SAMPLE_ATTEMPT_FREQ * 1.5 or real_sample_rate < SAMPLE_ATTEMPT_FREQ * 0.5:
            return SAMPLE_ATTEMPT_FREQ  
        
        return real_sample_rate


    def plot_frequency_spectrum(self, session_data):
        raw_values = np.array([d['raw_value'] for d in session_data])
        raw_values = raw_values - np.mean(raw_values) 
        Fs = self.calculate_real_sample_rate(session_data)
        if Fs is None:
            print("No hay suficientes datos para calcular la tasa de muestreo.")
            return
        
        n = len(raw_values)
        yf = fft(raw_values)
        xf = np.fft.fftfreq(n, 1 / Fs)

        plt.figure(figsize=(10, 6))
        plt.plot(xf[:n // 2], np.abs(yf[:n // 2]))
        plt.title('Espectro de Frecuencia')
        plt.xlabel('Frecuencia (Hz)')
        plt.ylabel('Amplitud')
        plt.show()

    def plot_power_spectrum(self, session_data):
        raw_values = np.array([d['raw_value'] for d in session_data])
        raw_values = raw_values - np.mean(raw_values)  
        Fs = self.calculate_real_sample_rate(session_data)
        if Fs is None:
            print("No hay suficientes datos para calcular la tasa de muestreo.")
            return
    
        n = len(raw_values)
        yf = fft(raw_values)
        xf = np.fft.fftfreq(n, 1 / Fs)
        power_spectrum = np.abs(yf[:n // 2]) ** 2

        plt.figure(figsize=(10, 6))
        plt.plot(xf[:n // 2], 10 * np.log10(power_spectrum))
        plt.title('Espectro de Potencia')
        plt.xlabel('Frecuencia (Hz)')
        plt.ylabel('Potencia (dB)')
        plt.show()

    def plot_spectrogram(self, session_data):
        raw_values = np.array([d['raw_value'] for d in session_data])
        raw_values = raw_values - np.mean(raw_values) 
        Fs = self.calculate_real_sample_rate(session_data)
        if Fs is None:
            print("No hay suficientes datos para calcular la tasa de muestreo.")
            return
        
        nperseg = int(Fs)
        noverlap = int(nperseg * 0.5)

        f, t, Sxx = spectrogram(raw_values, fs=Fs, nperseg=nperseg, noverlap=noverlap)

        plt.figure()
        plt.pcolormesh(t, f, 10 * np.log10(Sxx), cmap='jet')
        plt.colorbar()
        plt.xlabel('Tiempo [s]')
        plt.ylabel('Frecuencia [Hz]')
        plt.title('Espectrograma')
        plt.ylim([0, 30])  
        plt.show()

    def plot_spectrogram_with_sliders(self, session_data):
        raw_values = np.array([d['raw_value'] for d in session_data])
        raw_values = raw_values - np.mean(raw_values)
        Fs = self.calculate_real_sample_rate(session_data)
        if Fs is None:
            print("No hay suficientes datos para calcular la tasa de muestreo.")
            return
        
        total_samples = len(raw_values)
        total_time_minutes = total_samples / (Fs * 60)

        fig, ax = plt.subplots(figsize=(10, 6))
        plt.subplots_adjust(bottom=0.35)

        ax_slider_interval = plt.axes([0.1, 0.15, 0.8, 0.03], facecolor='lightgoldenrodyellow')
        ax_slider_pos = plt.axes([0.1, 0.05, 0.8, 0.03], facecolor='lightgoldenrodyellow')

        slider_interval = Slider(ax_slider_interval, 'Intervalo (min)', 0.1, total_time_minutes, valinit=1, valstep=0.1)
        slider_pos = Slider(ax_slider_pos, 'Posición (min)', 0, total_time_minutes - 0.1, valinit=0, valstep=0.1)

        def update(val):
            interval_minutes = slider_interval.val
            pos_minutes = slider_pos.val

            start_idx = int(pos_minutes * Fs * 60)
            end_idx = int(start_idx + interval_minutes * Fs * 60)

            if end_idx > total_samples:
                end_idx = total_samples

            raw_values_subset = raw_values[start_idx:end_idx]

            nperseg = int(Fs)
            noverlap = int(nperseg * 0.5)

            f, t, Sxx = spectrogram(raw_values_subset, fs=Fs, nperseg=nperseg, noverlap=noverlap)

            ax.clear()
            ax.pcolormesh(t, f, 10 * np.log10(Sxx), cmap='jet')
            ax.set_xlabel('Tiempo [s]')
            ax.set_ylabel('Frecuencia [Hz]')
            ax.set_title('Espectrograma')
            ax.set_ylim([0, 30])  
            fig.canvas.draw_idle()

        slider_interval.on_changed(update)
        slider_pos.on_changed(update)

        update(None)
        plt.show()

    def export_session_to_csv(self, session_data, filename):
        keys = session_data[0].keys()
        with open(filename, 'w', newline='') as output_file:
            dict_writer = csv.DictWriter(output_file, keys)
            dict_writer.writeheader()
            dict_writer.writerows(session_data)