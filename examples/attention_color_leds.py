import serial
import time
import sys
import os

# Ajusta esta ruta si tu módulo neurosky_interface está en otro lugar
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.neurosky_interface import NeuroSkyInterface

def main():
    # Solicitar puertos
    neurosky_port = input("Puerto para NeuroSky (ej. COM3 o /dev/ttyUSB0): ").strip()
    esp32_port = input("Puerto para ESP32 (ej. COM4 o /dev/ttyUSB1): ").strip()

    try:
        # 1. Conectar al MindWave / NeuroSky
        interface = NeuroSkyInterface(neurosky_port)
        print(f"Conectado a NeuroSky en {neurosky_port}")

        # 2. Conectar al ESP32 por serial
        esp32_serial = serial.Serial(esp32_port, baudrate=115200, timeout=1)
        print(f"Conectado al ESP32 en {esp32_port}")

        while True:
            # Leer el valor de meditación (usualmente 0–100, según la implementación)
            meditation_value = interface.meditation

            # Asegurarnos de no salir de 0–100 (por si el driver arroja valores fuera de rango)
            if meditation_value < 0:
                meditation_value = 0
            elif meditation_value > 100:
                meditation_value = 100

            # Enviar al ESP32 (terminamos con '\n' para que el ESP32 use readStringUntil('\n'))
            esp32_serial.write(f"{meditation_value}\n".encode())

            # Pequeña pausa
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("Interrupción recibida, saliendo...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Cerrar el serial y liberar si es necesario
        try:
            esp32_serial.close()
        except:
            pass
        print("Terminando script.")

if __name__ == "__main__":
    main()