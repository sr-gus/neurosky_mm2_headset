import csv
import serial
import time
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.neurosky_interface import NeuroSkyInterface
import threading

SAMPLE_FREQ = 512.0

class NeuroSkyDataCollector:
    def __init__(self, sample_freq=SAMPLE_FREQ, port=None, signal_type='raw', graph=False, csv_file='data.csv', save_to_csv=True):
        """
        Inicializa el recolector de datos del NeuroSky.
        :param sample_freq: Frecuencia de muestreo para la recolección de datos.
        :param port: Puerto serial al que está conectado el dispositivo NeuroSky.
        :param signal_type: Tipo de señal a recolectar ('raw', 'attention', 'meditation', etc.).
        :param graph: Si es True, se graficarán los datos en tiempo real.
        :param csv_file: Nombre del archivo CSV donde se guardarán los datos.
        :param save_to_csv: Si es True, se guardarán los datos en un archivo CSV.
        """
        self.port = port
        self.signal_type = signal_type
        self.graph = graph
        self.sample_freq = sample_freq
        self.raw_data = []
        self.running = False
        self.interface = None
        self.csv_file = csv_file
        self.save_to_csv = save_to_csv
        self.fig, self.ax, self.line = None, None, None
        self.data_thread = None  
        self.csv_writer = None  # Variable para manejar el archivo CSV
        self.csv_file_handle = None  # Manejador del archivo CSV

    def connect(self):
        """
        Conectar al dispositivo NeuroSky. Lanza una excepción si no es posible conectar.
        """
        try:
            if not self.port:
                raise ValueError("El puerto serial no ha sido especificado.")

            self.interface = NeuroSkyInterface(self.port)
            print(f"Conectado a NeuroSky en el puerto {self.port}.")
        except serial.SerialException as e:
            raise ConnectionError(f"Error de conexión con el puerto {self.port}: {e}")
        except Exception as e:
            raise ConnectionError(f"Error inesperado: {e}")

    def collect_data(self):
        """
        Recolectar datos del dispositivo de forma continua en un hilo separado. Detener con stop().
        """
        if not self.interface:
            raise ValueError("No se ha establecido conexión con el dispositivo.")
        
        self.running = True
        self.raw_data = []

        try:
            # Si se requiere guardar en CSV, abrir el archivo
            if self.save_to_csv:
                self.csv_file_handle = open(self.csv_file, mode='w', newline='')
                self.csv_writer = csv.writer(self.csv_file_handle)
                self.csv_writer.writerow(['Timestamp', self.signal_type.capitalize()])  # Escribir encabezados

            def collect():
                while self.running:
                    try:
                        signal_value = self.get_signal_value(self.signal_type)
                        self.raw_data.append(signal_value)

                        # Guardar en el CSV el valor con el tiempo actual (si se ha habilitado)
                        if self.save_to_csv:
                            self.csv_writer.writerow([time.time(), signal_value])
                            self.csv_file_handle.flush()  # Forzar escritura en disco

                        if len(self.raw_data) > 512:  # Limita los datos a los últimos 512 puntos
                            self.raw_data.pop(0)
                        time.sleep(1.0 / self.sample_freq)
                    except Exception as e:
                        print(f"Error durante la recolección de datos: {e}")
                        self.running = False

            # Iniciar el hilo de recolección de datos
            self.data_thread = threading.Thread(target=collect)
            self.data_thread.start()

        except IOError as e:
            print(f"Error al abrir o escribir en el archivo CSV: {e}")
            self.running = False

    def get_signal_value(self, signal_type):
        """
        Obtener el valor del tipo de señal especificado.
        :param signal_type: Tipo de señal a recolectar.
        :return: Valor de la señal especificada.
        """
        signal_mapping = {
            'raw': self.interface.raw_value,
            'attention': self.interface.attention,
            'meditation': self.interface.meditation,
            'blink': self.interface.blink,
            'delta': self.interface.waves.get('delta', 0),
            'theta': self.interface.waves.get('theta', 0),
            'low-alpha': self.interface.waves.get('low-alpha', 0),
            'high-alpha': self.interface.waves.get('high-alpha', 0),
            'low-beta': self.interface.waves.get('low-beta', 0),
            'high-beta': self.interface.waves.get('high-beta', 0),
            'low-gamma': self.interface.waves.get('low-gamma', 0),
            'mid-gamma': self.interface.waves.get('mid-gamma', 0)
        }
        return signal_mapping.get(signal_type, 0)

    def stop(self):
        """
        Detener la recolección de datos.
        """
        self.running = False
        if self.data_thread:
            self.data_thread.join()  
        if self.interface:
            self.interface.stop()
        if self.csv_file_handle:
            self.csv_file_handle.close()  # Cerrar el archivo CSV correctamente
        print("Recolección de datos detenida y archivo CSV cerrado.")

    def initialize_plot(self):
        """
        Inicializar la gráfica para actualización en tiempo real.
        """
        self.fig, self.ax = plt.subplots()
        self.line, = self.ax.plot([], [], lw=2)
        self.ax.set_title(f"{self.signal_type.capitalize()} Data")
        self.ax.set_xlabel("Tiempo (s)")
        self.ax.set_ylabel(f"{self.signal_type.capitalize()} Value")
        self.ax.set_xlim(0, 512)
        self.ax.set_ylim(-2048, 2048)

    def update_plot(self, frame):
        """
        Actualizar los datos en la gráfica en tiempo real.
        """
        self.line.set_data(range(len(self.raw_data)), self.raw_data)
        self.ax.set_xlim(0, len(self.raw_data))
        return self.line,

    def animate_plot(self):
        """
        Graficar en tiempo real los datos recolectados.
        """
        if not self.raw_data:
            print("No hay datos para graficar.")
            return

        self.initialize_plot()
        ani = FuncAnimation(self.fig, self.update_plot, blit=True, interval=100)
        plt.show()

    def print_data(self):
        """
        Imprimir los datos recolectados en la consola.
        """
        while self.running:
            if self.raw_data:
                print(f"{self.signal_type.capitalize()} Value: {self.raw_data[-1]}")
            time.sleep(1.0 / self.sample_freq)

    def get_latest_data(self):
        """
        Obtener los datos más recientes recolectados.
        :return: Lista de valores de señal recolectados.
        """
        return self.raw_data

def validate_signal_type(signal_type):
    """
    Valida si el tipo de señal es válido.
    :param signal_type: Tipo de señal proporcionada por el usuario.
    :raises ValueError: Si el tipo de señal no es válido.
    """
    valid_signals = ['raw', 'attention', 'meditation', 'blink', 'delta', 'theta', 
                     'low-alpha', 'high-alpha', 'low-beta', 'high-beta', 
                     'low-gamma', 'mid-gamma']

    if signal_type not in valid_signals:
        raise ValueError(f"Tipo de señal inválido: {signal_type}. Los tipos válidos son: {', '.join(valid_signals)}")


def main():
    try:
        port = input("Especifica el puerto serial (ej. COM3 o /dev/ttyUSB0): ").strip()
        signal_type = input("Especifica el tipo de señal (raw, attention, meditation, blink, delta, theta, low-alpha, high-alpha, low-beta, high-beta, low-gamma, mid-gamma): ").strip().lower()

        # Validar el tipo de señal
        validate_signal_type(signal_type)

        graph = input("¿Quieres graficar los datos en tiempo real? (s/n): ").strip().lower() == 's'
        
        # Preguntar si el usuario quiere guardar los datos en un archivo CSV
        save_to_csv = input("¿Quieres guardar los datos en un archivo CSV? (s/n): ").strip().lower() == 's'
        csv_file = ""
        if save_to_csv:
            csv_file = input("Especifica el nombre del archivo CSV donde guardar los datos (ej. data.csv): ").strip()

        collector = NeuroSkyDataCollector(SAMPLE_FREQ, port, signal_type, graph, csv_file, save_to_csv)
        collector.connect()

        if collector.interface is None:
            raise ValueError("No se pudo establecer conexión con el dispositivo.")

        if graph:
            collector.collect_data()
            collector.animate_plot()
        else:
            collector.collect_data()
            collector.print_data()  # Imprimir los datos en lugar de graficar

    except KeyboardInterrupt:
        print("Interrupción recibida, deteniendo recolección.")
    except Exception as e:
        print(f"Se produjo un error: {e}")
    finally:
        if 'collector' in locals():
            collector.stop()


if __name__ == "__main__":
    main()