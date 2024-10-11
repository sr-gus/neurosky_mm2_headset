from neurosky_mm2_headset.modules.neurosky_interface import NeuroSkyInterface
import matplotlib.pyplot as plt
import matplotlib.animation as animation

device_port = 'COM10'  # Cambia este valor al puerto correcto de tu dispositivo

interface = NeuroSkyInterface(device_port)

attention_data = []
meditation_data = []
max_samples = 1000  

fig, ax = plt.subplots(figsize=(10, 6))
ax.set_xlim(0, max_samples)
ax.set_ylim(0, 100)  
ax.set_title('Atención y Meditación en Tiempo Real')
ax.set_xlabel('Muestras')
ax.set_ylabel('Nivel')
attention_line, = ax.plot([], [], label='Atención', color='blue')
meditation_line, = ax.plot([], [], label='Meditación', color='green')
ax.legend(loc="upper right")

def update(frame):
    attention_data.append(interface.attention)
    meditation_data.append(interface.meditation)
    
    if len(attention_data) > max_samples:
        attention_data.pop(0)
    if len(meditation_data) > max_samples:
        meditation_data.pop(0)
    
    attention_line.set_data(range(len(attention_data)), attention_data)
    meditation_line.set_data(range(len(meditation_data)), meditation_data)
    
    return attention_line, meditation_line

ani = animation.FuncAnimation(fig, update, blit=True, interval=10)
plt.show()

interface.stop()
