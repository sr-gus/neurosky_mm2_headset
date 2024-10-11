from matplotlib import animation
import serial
from datetime import datetime
import time
import threading
import csv
import numpy as np
from numpy.fft import fft, rfft
from scipy.signal import spectrogram, butter, filtfilt
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
from matplotlib.dates import DateFormatter
from neurosky_mm2_headset.modules.neurosky_interface import NeuroSkyInterface

SAMPLE_ATTEMPT_FREQ = 500.0  # [Hz]
MAX_LIVE_SAMPLES = 1000
MAX_RECORDED_SAMPLES = 1000
ZERO_THRESHOLD = 1000
MAX_INTERVAL_MINUTES = 10
BATCH_SIZE = 1000
GRAPH_INTERVAL = 1000
X_AXIS_TYPE = 'log'
NORMALIZE_SXX = False

def butter_bandpass(lowcut, highcut, fs, order=4):
    nyquist = 0.5 * fs  # Frecuencia de Nyquist
    low = lowcut / nyquist
    high = highcut / nyquist
    b, a = butter(order, [low, high], btype='band')
    return b, a

def apply_bandpass_filter(data, lowcut, highcut, fs, order=4):
    b, a = butter_bandpass(lowcut, highcut, fs, order=order)
    y = filtfilt(b, a, data)
    return y

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
        self.plot_type = 'raw'
        self._data_count = 0
        self.max_Sxx_value = -np.inf
        self.power_lowcut = 12.0 
        self.power_highcut = 30.0  

    def connect_interface(self):
        try:
            self.interface = NeuroSkyInterface(self.device_port)
        except serial.SerialException as e:
            print(f'Error al conectar con el dispositivo NeuroSky: {e}')
            self.interface = None
        except Exception as e:
            print(f'Error inesperado al conectar con el dispositivo NeuroSky: {e}')
            self.interface = None

    def start_new_session(self, user_id):
        self.connect_interface()
        if self.interface is None:
            print('No se pudo iniciar la sesión debido a problemas de conexión con el MindWave.')
            self.end_session()
            return 

        self.current_session_id = self.db_manager.start_session(user_id)
        if self.current_session_id is None:
            print('No se pudo iniciar la sesión en la base de datos.')
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
                        print(f'Se han recibido {self.zero_count} ceros consecutivos. Posible desconexión.')
                        retries -= 1
                        if retries <= 0:
                            print('No se pudo recuperar la conexión después de varios intentos. Finalizando sesión.')
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

                    self._data_count += 1
                    time.sleep(1 / SAMPLE_ATTEMPT_FREQ)

                except serial.SerialException as e:
                    print(f'Error durante la recolección de datos: {e}')
                    retries -= 1
                    if retries <= 0:
                        print('Se superó el número máximo de reintentos. Finalizando sesión.')
                        self.end_session()
                        break
                except Exception as e:
                    print(f'Error inesperado durante la recolección de datos: {e}')
                    retries -= 1
                    if retries <= 0:
                        print('Se superó el número máximo de reintentos. Finalizando sesión.')
                        self.end_session()
                        break
            if data_batch:
                self.db_manager.save_data_batch(self.current_session_id, data_batch)

        self.collection_thread = threading.Thread(target=collect)
        self.collection_thread.daemon = True
        self.collection_thread.start()

    def set_plot_type(self, plot_type):
        self.plot_type = plot_type

    def initialize_plot(self):
        fig, ax = plt.subplots(figsize=(10, 6))
        
        if self.plot_type == 'raw':
            ax.set_xlim(0, MAX_LIVE_SAMPLES)
            ax.set_ylim(-2048, 2047)
            ax.set_title('Señal Cruda del EEG en Tiempo Real')
            ax.set_xlabel('Muestras')
            ax.set_ylabel('Amplitud (µV)')
            line, = ax.plot([], [], lw=2, color='red')

            def update_raw(frame):
                if len(self.raw_data) > MAX_LIVE_SAMPLES:
                    self.raw_data.pop(0)
                line.set_data(range(len(self.raw_data)), self.raw_data)
                return line,

            ani = animation.FuncAnimation(fig, update_raw, blit=True, interval=1/SAMPLE_ATTEMPT_FREQ)

        elif self.plot_type == 'frequency':
            ax.set_title('Espectro de Potencia en Tiempo Real')
            ax.set_xlabel('Frecuencia (Hz)')
            ax.set_ylabel('Amplitud (dB)') 

            def update_frequency(frame):
                if len(self.raw_data) >= GRAPH_INTERVAL:
                    raw_values = np.array(self.raw_data[-GRAPH_INTERVAL:])
                    self._data_count = 0
                    Fs = SAMPLE_ATTEMPT_FREQ
                    filtered_signal = apply_bandpass_filter(raw_values, self.power_lowcut, self.power_highcut, Fs, 6)

                    dt = 1 / Fs  
                    N = filtered_signal.shape[0]
                    T = N * dt

                    print(f'Filtered mean: {filtered_signal.mean()}')

                    xf = fft(filtered_signal - filtered_signal.mean())
                    Sxx = 2 * dt ** 2 / T * (xf * xf.conj())
                    Sxx = Sxx[:int(len(filtered_signal) / 2)]

                    Sxx = np.maximum(Sxx.real, 1e-10)

                    print(f'Filtered Sxx mean: {Sxx.mean()}')

                    df = 1 / T
                    fNQ = 1 / dt / 2
                    faxis = np.arange(0, fNQ, df)

                    limit_index = np.where((faxis >= 12) & (faxis <= 30))[0]
                    faxis_limited = faxis[limit_index]
                    Sxx_limited = Sxx[limit_index]

                    print(f'Filtered Sxx_limited mean: {Sxx_limited.mean()}')

                    ax.clear()
                    ax.set_xlim([12, 30])

                    if NORMALIZE_SXX:
                        ax.set_ylim([-60, 0])
                        ax.plot(faxis_limited, 10 * np.log10(Sxx_limited / np.max(Sxx_limited)))
                    else:
                        ax.set_ylim([-10, 500])
                        ax.plot(faxis_limited, Sxx_limited)

                    if X_AXIS_TYPE == 'log':
                        ax.set_xscale('log')
                    else:
                        ax.set_xscale('linear')

                return ax,

            ani = animation.FuncAnimation(fig, update_frequency, interval=1000)

        elif self.plot_type == 'spectrogram':
            ax.set_title('Espectrograma en Tiempo Real')
            ax.set_xlabel('Tiempo [s]')
            ax.set_ylabel('Frecuencia [Hz]')

            def update_spectrogram(frame):
                if (len(self.raw_data) >= GRAPH_INTERVAL):
                    raw_values = np.array(self.raw_data[-self._data_count:])
                    self._data_count = 0
                    Fs = SAMPLE_ATTEMPT_FREQ
                    f, t, Sxx = spectrogram(raw_values, fs=Fs, nperseg=int(Fs), noverlap=int(Fs*0.95))
                    self.max_Sxx_value = max(self.max_Sxx_value, np.max(Sxx))
                    print(self.max_Sxx_value)
                    ax.clear()
                    pcm = ax.pcolormesh(t, f, 10 * np.log10(Sxx), cmap='jet', vmin=0, vmax=10 * np.log10(10000))
                    ax.set_ylim([0, 30])

                return ax,

            ani = animation.FuncAnimation(fig, update_spectrogram, interval=1000)

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


    def plot_power_spectrum(self, session_data):
        raw_values = np.array([d['raw_value'] for d in session_data])
        Fs = self.calculate_real_sample_rate(session_data)
        if Fs is None:
            print('No hay suficientes datos para calcular la tasa de muestreo.')
            return
        dt = 1 / Fs  
        N = raw_values.shape[0]
        T = N * dt

        xf = fft(raw_values - raw_values.mean())  
        Sxx = 2 * dt ** 2 / T * (xf * xf.conj())  
        Sxx = Sxx[:int(len(raw_values) / 2)] 

        Sxx = np.maximum(Sxx.real, 1e-10)

        df = 1 / T
        fNQ = 1 / dt / 2
        faxis = np.arange(0, fNQ, df)

        plt.figure(figsize=(10, 6))
        plt.ylim([-60, 0])
        plt.plot(faxis, 10 * np.log10(Sxx.real / max(Sxx.real)))  
        plt.title('Espectro de Potencia')
        plt.xlabel('Frecuencia (Hz)')
        plt.ylabel('Amplitud [dB]')
        plt.show()

    def plot_spectrogram(self, session_data):
        raw_values = np.array([d['raw_value'] for d in session_data])
        Fs = self.calculate_real_sample_rate(session_data)
        if Fs is None:
            print('No hay suficientes datos para calcular la tasa de muestreo.')
            return
        

        nperseg = int(Fs)
        noverlap = int(nperseg * 0.95)

        f, t, Sxx = spectrogram(raw_values, fs=Fs, nperseg=nperseg, noverlap=noverlap)

        plt.figure()
        plt.pcolormesh(t, f, 10 * np.log10(Sxx), cmap='jet')
        plt.colorbar()
        plt.xlabel('Tiempo [s]')
        plt.ylabel('Frecuencia [Hz]')
        plt.title('Espectrograma')
        plt.ylim([0, 100])  
        plt.show()

    def plot_power_spectrum_with_sliders(self, session_data):
        raw_values = np.array([d['raw_value'] for d in session_data])
        Fs = self.calculate_real_sample_rate(session_data)
        if Fs is None:
            print('No hay suficientes datos para calcular la tasa de muestreo.')
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

            dt = 1 / Fs  
            N = raw_values_subset.shape[0]
            T = N * dt

            xf = fft(raw_values_subset - raw_values_subset.mean())  
            Sxx = 2 * dt ** 2 / T * (xf * xf.conj())  
            Sxx = Sxx[:N // 2] 

            Sxx = np.maximum(Sxx.real, 1e-10)

            df = 1 / T
            fNQ = 1 / dt / 2
            faxis = np.arange(0, fNQ, df)[:N // 2] 

            ax.clear()
            ax.set_ylim([-60, 0])  
            ax.plot(faxis, 10 * np.log10(Sxx.real / max(Sxx.real))) 
            ax.set_xlabel('Frecuencia [Hz]')
            ax.set_ylabel('Amplitud [dB]')
            ax.set_title('Espectro de Potencia')

            fig.canvas.draw_idle()

        slider_interval.on_changed(update)
        slider_pos.on_changed(update)

        update(None)
        plt.show()

    def plot_spectrogram_with_sliders(self, session_data):
        raw_values = np.array([d['raw_value'] for d in session_data])
        raw_values = raw_values - np.mean(raw_values)
        Fs = self.calculate_real_sample_rate(session_data)
        if Fs is None:
            print('No hay suficientes datos para calcular la tasa de muestreo.')
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
            noverlap = int(nperseg * 0.95)

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