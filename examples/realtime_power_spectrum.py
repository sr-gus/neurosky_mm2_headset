import serial
import numpy as np
from scipy.signal import butter, filtfilt, spectrogram
from numpy.fft import fft
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import time
import threading

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.neurosky_interface import NeuroSkyInterface
import signal

SAMPLE_FREQ = 10000.0
TIME_SLEEP = 1.0 / SAMPLE_FREQ
GRAPH_INTERVAL = 5000
MAX_LIVE_SAMPLES = 5000
POWER_LOW_CUT = 12.0
POWER_HIGH_CUT = 30.0
X_AXIS_TYPE = 'log'
NORMALIZE_SXX = False

def butter_bandpass(lowcut, highcut, fs, order=4):
    nyquist = 0.5 * fs
    low = lowcut / nyquist
    high = highcut / nyquist
    b, a = butter(order, [low, high], btype='band')
    return b, a

def apply_bandpass_filter(data, lowcut, highcut, fs, order=4):
    b, a = butter_bandpass(lowcut, highcut, fs, order=order)
    y = filtfilt(b, a, data)
    return y

class RealTimePowerSpectrum:
    def __init__(self, port, serial_port=None):
        self.port = port
        self.raw_data = []
        self.low_beta_value = 0
        self.high_beta_value = 0
        self.collecting = False
        self.collection_thread = None
        self.serial_connection = None
        self.sxx_mean_history = []
        self.spectrogram_sxx_max_history = []

        if serial_port:
            self.serial_connection = serial.Serial(serial_port, baudrate=115200, timeout=1)

    def connect_interface(self):
        try:
            self.interface = NeuroSkyInterface(self.port)
        except serial.SerialException as e:
            print(f'Error al conectar con el dispositivo NeuroSky: {e}')
            self.interface = None
        except Exception as e:
            print(f'Error inesperado al conectar con el dispositivo NeuroSky: {e}')
            self.interface = None

    def start_collection(self):
        self.connect_interface()
        if self.interface is None:
            print('No se pudo iniciar la sesión debido a problemas de conexión con el MindWave.')
            sys.exit(1) 

        self.collecting = True
        self.collection_thread = threading.Thread(target=self.collect_data)
        self.collection_thread.start()

    def stop_collection(self):
        self.collecting = False
        if self.collection_thread:
            self.collection_thread.join()

    def collect_data(self):
        while self.collecting:
            try:
                raw_value = self.interface.raw_value
                self.raw_data.append(raw_value)

                if 'low-beta' in self.interface.waves.keys():
                    self.low_beta_value = self.interface.waves['low-beta']
                if 'high-beta' in self.interface.waves.keys():
                    self.high_beta_value = self.interface.waves['high-beta']

                if len(self.raw_data) > MAX_LIVE_SAMPLES:
                    self.raw_data.pop(0)
                time.sleep(TIME_SLEEP)
            except Exception as e:
                print(f'Error durante la recolección de datos: {e}')
                self.collecting = False
                sys.exit(1) 

    def initialize_plot(self):
        fig1, ax1 = plt.subplots(figsize=(10, 6))
        ax1.set_title('Espectro de Potencia en Tiempo Real')
        ax1.set_xlabel('Frecuencia (Hz)')
        ax1.set_ylabel('Amplitud (dB)')

        fig2, ax2 = plt.subplots(figsize=(10, 6))
        ax2.set_title('Señal Cruda en Tiempo Real')
        ax2.set_xlabel('Tiempo (s)')
        ax2.set_ylabel('Amplitud')

        fig3, ax3 = plt.subplots(figsize=(10, 6))
        ax3.set_title('Espectrograma en Tiempo Real')
        ax3.set_xlabel('Tiempo [s]')
        ax3.set_ylabel('Frecuencia [Hz]')
        cbar = None

        def update_spectrum(frame):
            if len(self.raw_data) >= GRAPH_INTERVAL:
                raw_values = np.array(self.raw_data[-GRAPH_INTERVAL:])
                Fs = 512
                filtered_signal = apply_bandpass_filter(raw_values, POWER_LOW_CUT, POWER_HIGH_CUT, Fs, 2)
                print(f'Filtered signal mean: {filtered_signal.mean()}')  

                dt = 1 / Fs  
                N = filtered_signal.shape[0]
                T = N * dt

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

                '''
                Cálculo del valor promedio para las bandas de beta baja y beta alta
                low_beta_index = np.where((faxis_limited >= 12) & (faxis_limited <= 15))[0]
                low_beta_power = Sxx_limited[low_beta_index].mean()

                high_beta_index = np.where((faxis_limited >= 15) & (faxis_limited <= 30))[0]
                high_beta_power = Sxx_limited[high_beta_index].mean()
                '''

                Sxx_mean = Sxx_limited.mean()
                print(f'Filtered Sxx_limited mean: {Sxx_mean}')  # Debug print
                '''
                print(f'Low Beta Value: {self.low_beta_value}')
                print(f'Low Beta Calculated: {low_beta_power}')
                print(f'High Beta Value: {self.high_beta_value}')
                print(f'High Beta Calculated: {high_beta_power}')
                '''

                self.sxx_mean_history.append(Sxx_mean)
                if len(self.sxx_mean_history) > 100:
                    self.sxx_mean_history.pop(0)

                log_sxx_mean_history = np.log10(self.sxx_mean_history)

                min_log_sxx = np.min(log_sxx_mean_history)
                max_log_sxx = np.max(log_sxx_mean_history)

                if max_log_sxx - min_log_sxx == 0:
                    scaled_value = 50
                else:
                    current_log_sxx = np.log10(Sxx_mean)
                    normalized_value = (current_log_sxx - min_log_sxx) / (max_log_sxx - min_log_sxx)
                    gamma = 2  
                    scaled_value = 100 * normalized_value ** gamma
                    scaled_value = max(0, min(100, scaled_value))

                print(f'Scaled Value: {scaled_value}')  
                if self.serial_connection:
                    try:
                        self.serial_connection.write(f"{scaled_value}\n".encode())
                    except Exception as e:
                        print(f'Error enviando dato al serial: {e}')

                ax1.clear()
                ax1.set_title('Espectro de Potencia en Tiempo Real')
                ax1.set_xlabel('Frecuencia (Hz)')
                ax1.set_ylabel('Amplitud (dB)')
                ax1.set_xlim([12, 30])
                ax1.set_ylim([-60, 0] if NORMALIZE_SXX else [-10, 500])
                ax1.plot(faxis_limited, 10 * np.log10(Sxx_limited) if NORMALIZE_SXX else Sxx_limited)
                ax1.set_xscale(X_AXIS_TYPE)

            return ax1,
                
        def update_raw_signal(frame):
            if len(self.raw_data) >= GRAPH_INTERVAL:
                raw_values = np.array(self.raw_data[-GRAPH_INTERVAL:])
                time_axis = np.arange(len(raw_values)) / SAMPLE_FREQ

                ax2.clear()
                ax2.set_title('Señal Cruda en Tiempo Real')
                ax2.set_xlabel('Tiempo (s)')
                ax2.set_ylabel('Amplitud')
                ax2.plot(time_axis, raw_values)
                ax2.set_xlim([time_axis[0], time_axis[-1]])
                ax2.set_ylim(-500, 500)

            return ax2,

        def update_spectrogram(frame):
            if len(self.raw_data) >= GRAPH_INTERVAL:
                raw_values = np.array(self.raw_data[-GRAPH_INTERVAL:])
                Fs = 512
                f, t, Sxx = spectrogram(raw_values, fs=Fs, nperseg=int(Fs), noverlap=int(Fs*0.95))

                max_Sxx = np.max(Sxx)
                self.spectrogram_sxx_max_history.append(max_Sxx)
                if len(self.spectrogram_sxx_max_history) > 100:
                    self.spectrogram_sxx_max_history.pop(0)

                ax3.clear()
                ax3.set_title('Espectrograma en Tiempo Real')
                ax3.set_xlabel('Tiempo [s]')
                ax3.set_ylabel('Frecuencia [Hz]')
                pcm = ax3.pcolormesh(t, f, 10 * np.log10(Sxx), cmap='jet', vmin=0, vmax=10 * np.log10(5000))
                ax3.set_ylim([0, 30])
                nonlocal cbar
                if cbar is None:
                    cbar = fig3.colorbar(pcm, ax=ax3)
                    cbar.set_label('Amplitud (dB)')
                else:
                    cbar.update_normal(pcm)

            return ax3,

        ani1 = FuncAnimation(fig1, update_spectrum, interval=1000, cache_frame_data=False)
        ani2 = FuncAnimation(fig2, update_raw_signal, interval=100, cache_frame_data=False)
        ani3 = FuncAnimation(fig3, update_spectrogram, interval=5000, cache_frame_data=False)

        def on_close(event):
            self.stop_collection()
            print("Recolección de datos detenida.")
            plt.close(event.canvas.figure)

        fig1.canvas.mpl_connect('close_event', on_close)
        fig2.canvas.mpl_connect('close_event', on_close)
        fig3.canvas.mpl_connect('close_event', on_close)

        plt.show()

if __name__ == "__main__":
    port = 'COM10'  
    serial_port = 'COM3' 
    spectrum_visualizer = RealTimePowerSpectrum(port, serial_port)

    def signal_handler(sig, frame):
        print("\nInterrupción recibida, cerrando...")
        spectrum_visualizer.stop_collection()
        plt.close('all')
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        spectrum_visualizer.start_collection()
        spectrum_visualizer.initialize_plot()
    except KeyboardInterrupt:
        spectrum_visualizer.stop_collection()
        plt.close('all')
        print("Recolección de datos detenida.")
        sys.exit(0)