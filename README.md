
# NeuroSky MindWave Mobile - Configuración y Uso

Este proyecto te permite recolectar, visualizar y guardar datos del dispositivo **NeuroSky MindWave Mobile** utilizando Python. A continuación, se detallan los pasos para configurar el dispositivo, habilitar el puerto COM en Windows, ejecutar el código y ejemplos de uso para recolectar señales EEG.

## Requisitos

### Instalación de Dependencias

Antes de comenzar, asegúrate de tener instaladas las siguientes dependencias. Puedes instalarlas ejecutando el siguiente comando en tu terminal:

```bash
pip install -r requirements.txt
```

El archivo `requirements.txt` incluye las siguientes bibliotecas necesarias para la comunicación con el MindWave Mobile, el procesamiento de señales y la visualización gráfica:

```
pyserial>=3.5
numpy>=1.23.5  
scipy>=1.11.2  
matplotlib>=3.8.0
```

Estas bibliotecas permiten la comunicación serial, el procesamiento de señales y la visualización gráfica de los datos.

## Configuración del MindWave Mobile

### 1. Emparejar el MindWave Mobile por Bluetooth

Sigue estos pasos para conectar el dispositivo MindWave Mobile a tu ordenador mediante Bluetooth:

- **Activar Bluetooth en tu ordenador:**

  Ve a la configuración de Bluetooth en tu sistema operativo y asegúrate de que esté activado.

- **Buscar el dispositivo MindWave Mobile:**

  En la lista de dispositivos Bluetooth disponibles, selecciona el dispositivo MindWave Mobile.
  Si se te pide un código de emparejamiento, ingresa `0000` (cuatro ceros).

- **Emparejar el dispositivo:**

  Finaliza el proceso de emparejamiento y asegúrate de que el dispositivo esté conectado correctamente.

### 2. Habilitar Manualmente el Puerto COM en Windows

Después de emparejar el dispositivo, debes habilitar el puerto COM de manera manual en Windows. Aquí están los pasos para hacerlo:

1. **Abrir el Administrador de Dispositivos:**

   Presiona las teclas `Win + X` y selecciona _Administrador de dispositivos_.

2. **Buscar el puerto COM en Puertos (COM y LPT):**

   En el Administrador de dispositivos, expande la sección Puertos (COM y LPT) y busca un dispositivo llamado MindWave Mobile.
   Anota el número de puerto COM que aparece junto a su nombre, como COM3, COM4, etc.

3. **Habilitar el puerto COM:**

   Si el dispositivo aparece como deshabilitado, haz clic derecho y selecciona _Habilitar dispositivo_.

4. **Verificar las propiedades del puerto:**

   Haz clic derecho sobre el puerto del MindWave Mobile y selecciona _Propiedades_.
   Verifica en la pestaña _Configuración del puerto_ que todo esté correctamente configurado.

Este puerto COM será el que utilizarás más adelante en el código para establecer la conexión con el dispositivo.

## Ejecución del Código Principal

### 1. Ejecutar el Script

Para comenzar a recolectar datos de tu dispositivo MindWave Mobile, simplemente ejecuta el siguiente comando en tu terminal:

```bash
python neurosky_data_collector.py
```

### 2. Instrucciones en la Terminal

Durante la ejecución del script, se te pedirá que ingreses algunos parámetros clave:

- **Especifica el puerto serial (COM):**

  Ingresarás el puerto COM que anotaste previamente (ej. COM3).

- **Especifica el tipo de señal:**

  Puedes seleccionar entre varios tipos de señales como `raw`, `attention`, `meditation`, `blink`, `delta`, `theta`, `low-alpha`, `high-alpha`, `low-beta`, `high-beta`, `low-gamma`, `mid-gamma`.

- **¿Quieres graficar los datos en tiempo real?**

  Si quieres visualizar una gráfica en tiempo real, responde `s`. Si prefieres solo recolectar datos sin visualización, responde `n`.

- **¿Quieres guardar los datos en un archivo CSV?**

  Si deseas guardar los datos en un archivo CSV, responde `s`. Se te pedirá que especifiques el nombre del archivo, como `data.csv`.

## Ejemplos de Uso

### 1. Recolección de Datos y Almacenamiento en un CSV

Este ejemplo muestra cómo recolectar los valores `raw` del MindWave Mobile y guardarlos en un archivo CSV llamado `data.csv`:

```python
from neurosky_data_collector import NeuroSkyDataCollector

# Configuración del puerto COM y tipo de señal
port = "COM3"  # Cambia esto al puerto COM que hayas configurado
signal_type = "raw"

# Crear el recolector de datos y conectarlo
collector = NeuroSkyDataCollector(port=port, signal_type=signal_type, save_to_csv=True, csv_file='data.csv')
collector.connect()

# Recolectar los datos y guardarlos en un archivo CSV
collector.collect_data()

# Cuando termines de recolectar datos, llama al método stop para detener la conexión
collector.stop()
```

### 2. Visualización de Datos en Tiempo Real

Este ejemplo muestra cómo recolectar la señal `attention` del MindWave Mobile y visualizarla en tiempo real utilizando gráficos de Matplotlib:

```python
from neurosky_data_collector import NeuroSkyDataCollector

# Configuración del puerto COM y tipo de señal
port = "COM3"  # Cambia esto al puerto COM que hayas configurado
signal_type = "attention"

# Crear el recolector de datos y conectarlo
collector = NeuroSkyDataCollector(port=port, signal_type=signal_type, graph=True)
collector.connect()

# Recolectar y graficar los datos en tiempo real
collector.collect_data()
collector.animate_plot()  # Inicia la animación de la gráfica
```

### 3. Recolección de Datos sin CSV ni Gráficas

Este ejemplo recolecta los datos de la señal `meditation` y los imprime en la consola sin guardarlos en un CSV ni visualizarlos gráficamente:

```python
from neurosky_data_collector import NeuroSkyDataCollector

# Configuración del puerto COM y tipo de señal
port = "COM3"  # Cambia esto al puerto COM que hayas configurado
signal_type = "meditation"

# Crear el recolector de datos y conectarlo
collector = NeuroSkyDataCollector(port=port, signal_type=signal_type, save_to_csv=False, graph=False)
collector.connect()

# Recolectar e imprimir los datos
collector.collect_data()
collector.print_data()  # Imprime los valores en la consola
```

### 4. Usar Datos de attention para Controlar Eventos en Tiempo Real
En este ejemplo, usaremos los datos de attention en tiempo real para activar una función (simulada como una impresión en consola) cuando el valor de atención supere un determinado umbral (por ejemplo, 60).

```python
from neurosky_data_collector import NeuroSkyDataCollector

# Configuración del puerto COM y tipo de señal
port = "COM3"  # Cambia esto al puerto COM que hayas configurado
signal_type = "attention"

# Umbral de atención para activar un evento
attention_threshold = 60

# Función que se activa cuando el valor de atención supera el umbral
def attention_event():
    print("¡Atención elevada! Evento activado.")

# Crear el recolector de datos y conectarlo
collector = NeuroSkyDataCollector(port=port, signal_type=signal_type, graph=False, save_to_csv=False)
collector.connect()

# Recolectar los datos en tiempo real y activar eventos
try:
    while True:
        collector.collect_data()  # Recolecta datos
        latest_attention = collector.get_latest_data()[-1] if collector.raw_data else 0  # Obtén el último valor
        print(f"Nivel de atención actual: {latest_attention}")

        # Activar el evento si el nivel de atención supera el umbral
        if latest_attention > attention_threshold:
            attention_event()
        
        # Pausar ligeramente para evitar sobrecarga de la CPU
        time.sleep(0.5)
except KeyboardInterrupt:
    print("Interrupción recibida. Deteniendo...")
finally:
    collector.stop()
```