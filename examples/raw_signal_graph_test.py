from neurosky_mm2_headset.modules.neurosky_interface import NeuroSkyInterface
import matplotlib.pyplot as plt
import matplotlib.animation as animation

device_port = 'COM10'  # Cambia este valor al puerto correcto de tu dispositivo

interface = NeuroSkyInterface(device_port)

raw_data = []
max_samples = 1000  

fig, ax = plt.subplots(figsize=(10, 6))
ax.set_xlim(0, max_samples)
ax.set_ylim(-2048, 2047) 
ax.set_title('Señal Cruda del EEG en Tiempo Real')
ax.set_xlabel('Muestras')
ax.set_ylabel('Amplitud (µV)')
line, = ax.plot([], [], lw=2, color='red')

def update(frame):
    raw_data.append(interface.raw_value)
    if len(raw_data) > max_samples:
        raw_data.pop(0)
    line.set_data(range(len(raw_data)), raw_data)
    return line,

ani = animation.FuncAnimation(fig, update, blit=True, interval=10)

plt.show()

interface.stop()
