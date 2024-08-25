import time
from neurosky_interface import NeuroSkyInterface

device_port = 'COM10'  # Asegúrate de que este es el puerto correcto
interface = NeuroSkyInterface(device_port)

def print_raw_signal(interface):
    """Función para imprimir la señal cruda en la consola."""
    while True:
        print(f"Señal cruda: {interface.raw_value} µV")
        time.sleep(0.1) 

try:
    print_raw_signal(interface)
except KeyboardInterrupt:
    print("Finalizando...")
    interface.stop()
