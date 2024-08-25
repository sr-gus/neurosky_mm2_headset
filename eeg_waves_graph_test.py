from neurosky_interface import NeuroSkyInterface
import matplotlib.pyplot as plt
import matplotlib.animation as animation

device_port = 'COM10'  # Cambia este valor al puerto correcto de tu dispositivo

interface = NeuroSkyInterface(device_port)

eeg_data = {
    'delta': [],
    'theta': [],
    'low-alpha': [],
    'high-alpha': [],
    'low-beta': [],
    'high-beta': [],
    'low-gamma': [],
    'mid-gamma': []
}
max_samples = 1000 

fig, axs = plt.subplots(8, 1, figsize=(10, 18), sharex=True)
fig.suptitle('Ondas EEG en Tiempo Real')

wave_types = list(eeg_data.keys())
y_limits = {
    'delta': (0, 1000000),
    'theta': (0, 500000),
    'low-alpha': (0, 300000),
    'high-alpha': (0, 300000),
    'low-beta': (0, 200000),
    'high-beta': (0, 200000),
    'low-gamma': (0, 100000),
    'mid-gamma': (0, 100000)
}

lines = {}
for i, wave_type in enumerate(wave_types):
    axs[i].set_title('')
    axs[i].set_xlim(0, max_samples)
    axs[i].set_ylim(y_limits[wave_type])
    if (wave_type == 'high-alpha'):
        axs[i].set_ylabel('Amplitud (µV²)')
    lines[wave_type], = axs[i].plot([], [], label=wave_type)
    axs[i].legend(loc="upper right")
axs[-1].set_xlabel('Muestras')

def update(frame):
    for wave_type in eeg_data.keys():
        eeg_data[wave_type].append(interface.waves.get(wave_type, 0))
        if len(eeg_data[wave_type]) > max_samples:
            eeg_data[wave_type].pop(0)
    
    for wave_type, line in lines.items():
        line.set_data(range(len(eeg_data[wave_type])), eeg_data[wave_type])
    
    return list(lines.values())

ani = animation.FuncAnimation(fig, update, blit=True, interval=10)
plt.show()

interface.stop()
