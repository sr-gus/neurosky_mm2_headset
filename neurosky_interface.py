import serial
import threading
import struct

class NeuroSkyInterface:
    """
    Interfaz para comunicarse con el dispositivo MindWave Mobile.
    """

    # Constantes del dispositivo MindWave
    CONNECT = b'\xc0'
    DISCONNECT = b'\xc1'
    AUTOCONNECT = b'\xc2'
    SYNC = b'\xaa'
    EXCODE = b'\x55'
    POOR_SIGNAL = b'\x02'
    ATTENTION = b'\x04'
    MEDITATION = b'\x05'
    BLINK = b'\x16'
    HEADSET_CONNECTED = b'\xd0'
    HEADSET_NOT_FOUND = b'\xd1'
    HEADSET_DISCONNECTED = b'\xd2'
    REQUEST_DENIED = b'\xd3'
    STANDBY_SCAN = b'\xd4'
    RAW_VALUE = b'\x80'
    ASIC_EEG_POWER = b'\x83'

    STATUS_CONNECTED = 'connected'
    STATUS_SCANNING = 'scanning'
    STATUS_STANDBY = 'standby'

    class SerialListener(threading.Thread):
        """
        Hilo para manejar la recepción de datos del dispositivo NeuroSky.
        """

        def __init__(self, interface, *args, **kwargs):
            """Inicializa el listener serial."""
            self.interface = interface
            self.counter = 0
            super().__init__(*args, **kwargs)

        def run(self):
            """Escucha continuamente los paquetes de datos entrantes."""
            s = self.interface.dongle
            self.interface.running = True

            # Configuración del puerto serial para asegurar la conexión
            s.write(NeuroSkyInterface.DISCONNECT)
            d = s.getSettingsDict()
            for i in range(2):
                d['rtscts'] = not d['rtscts']
                s.applySettingsDict(d)

            while self.interface.running:
                try:
                    if s.read() == NeuroSkyInterface.SYNC and s.read() == NeuroSkyInterface.SYNC:
                        # Longitud del paquete
                        while True:
                            plength = int.from_bytes(s.read(), byteorder='big')
                            if plength != 170:
                                break
                        if plength > 170:
                            continue

                        # Lee el payload
                        payload = s.read(plength)

                        # Verifica el checksum
                        val = sum(b for b in payload[:-1])
                        val &= 0xff
                        val = ~val & 0xff
                        chksum = int.from_bytes(s.read(), byteorder='big')

                        self.parse_payload(payload)
                except serial.SerialException:
                    break
                except OSError:
                    break

            print('Cerrando conexión...')
            if s and s.isOpen():
                s.close()

        def parse_payload(self, payload):
            """Procesa el payload recibido."""
            while payload:
                excode = 0
                try:
                    code, payload = payload[0], payload[1:]
                    code_char = struct.pack('B', code)
                    self.interface.count = self.counter
                    self.counter += 1
                    if self.counter >= 100:
                        self.counter = 0
                except IndexError:
                    pass

                while code_char == NeuroSkyInterface.EXCODE:
                    excode += 1
                    try:
                        code, payload = payload[0], payload[1:]
                    except IndexError:
                        pass

                if code < 0x80:
                    try:
                        value, payload = payload[0], payload[1:]
                    except IndexError:
                        pass
                    if code_char == NeuroSkyInterface.POOR_SIGNAL:
                        old_poor_signal = self.interface.poor_signal
                        self.interface.poor_signal = value
                        if self.interface.poor_signal > 0:
                            if old_poor_signal == 0:
                                for handler in self.interface.poor_signal_handlers:
                                    handler(self.interface, self.interface.poor_signal)
                        else:
                            if old_poor_signal > 0:
                                for handler in self.interface.good_signal_handlers:
                                    handler(self.interface, self.interface.poor_signal)
                    elif code_char == NeuroSkyInterface.ATTENTION:
                        self.interface.attention = value
                        for handler in self.interface.attention_handlers:
                            handler(self.interface, self.interface.attention)
                    elif code_char == NeuroSkyInterface.MEDITATION:
                        self.interface.meditation = value
                        for handler in self.interface.meditation_handlers:
                            handler(self.interface, self.interface.meditation)
                    elif code_char == NeuroSkyInterface.BLINK:
                        self.interface.blink = value
                        for handler in self.interface.blink_handlers:
                            handler(self.interface, self.interface.blink)
                else:
                    try:
                        vlength, payload = payload[0], payload[1:]
                    except IndexError:
                        continue
                    value, payload = payload[:vlength], payload[vlength:]

                    if code_char == NeuroSkyInterface.RAW_VALUE and len(value) >= 2:
                        raw = value[0] * 256 + value[1]
                        if raw >= 32768:
                            raw -= 65536
                        self.interface.raw_value = raw
                        for handler in self.interface.raw_value_handlers:
                            handler(self.interface, self.interface.raw_value)
                    if code_char == NeuroSkyInterface.HEADSET_CONNECTED:
                        run_handlers = self.interface.status != NeuroSkyInterface.STATUS_CONNECTED
                        self.interface.status = NeuroSkyInterface.STATUS_CONNECTED
                        self.interface.headset_id = value.encode('hex')
                        if run_handlers:
                            for handler in self.interface.headset_connected_handlers:
                                handler(self.interface)
                    elif code_char == NeuroSkyInterface.HEADSET_NOT_FOUND:
                        if vlength > 0:
                            not_found_id = value.encode('hex')
                            for handler in self.interface.headset_notfound_handlers:
                                handler(self.interface, not_found_id)
                        else:
                            for handler in self.interface.headset_notfound_handlers:
                                handler(self.interface, None)
                    elif code_char == NeuroSkyInterface.HEADSET_DISCONNECTED:
                        headset_id = value.encode('hex')
                        for handler in self.interface.headset_disconnected_handlers:
                            handler(self.interface, headset_id)
                    elif code_char == NeuroSkyInterface.REQUEST_DENIED:
                        for handler in self.interface.request_denied_handlers:
                            handler(self.interface)
                    elif code_char == NeuroSkyInterface.STANDBY_SCAN:
                        try:
                            byte = value[0]
                        except IndexError:
                            byte = None
                        if byte:
                            run_handlers = self.interface.status != NeuroSkyInterface.STATUS_SCANNING
                            self.interface.status = NeuroSkyInterface.STATUS_SCANNING
                            if run_handlers:
                                for handler in self.interface.scanning_handlers:
                                    handler(self.interface)
                        else:
                            run_handlers = self.interface.status != NeuroSkyInterface.STATUS_STANDBY
                            self.interface.status = NeuroSkyInterface.STATUS_STANDBY
                            if run_handlers:
                                for handler in self.interface.standby_handlers:
                                    handler(self.interface)
                    elif code_char == NeuroSkyInterface.ASIC_EEG_POWER:
                        j = 0
                        for i in ['delta', 'theta', 'low-alpha', 'high-alpha', 'low-beta', 'high-beta', 'low-gamma', 'mid-gamma']:
                            self.interface.waves[i] = value[j] * 255 * 255 + value[j + 1] * 255 + value[j + 2]
                            j += 3
                        for handler in self.interface.waves_handlers:
                            handler(self.interface, self.interface.waves)

    def __init__(self, device, headset_id=None, open_serial=True):
        """Inicializa la interfaz con el dispositivo."""
        self.dongle = None
        self.listener = None
        self.device = device
        self.headset_id = headset_id
        self.poor_signal = 255
        self.attention = 0
        self.meditation = 0
        self.blink = 0
        self.raw_value = 0
        self.waves = {}
        self.status = None
        self.count = 0
        self.running = False

        # Manejadores de eventos
        self.poor_signal_handlers = []
        self.good_signal_handlers = []
        self.attention_handlers = []
        self.meditation_handlers = []
        self.blink_handlers = []
        self.raw_value_handlers = []
        self.waves_handlers = []
        self.headset_connected_handlers = []
        self.headset_notfound_handlers = []
        self.headset_disconnected_handlers = []
        self.request_denied_handlers = []
        self.scanning_handlers = []
        self.standby_handlers = []

        if open_serial:
            self.serial_open()

    def serial_open(self):
        """Abre la conexión serial y comienza a escuchar los datos."""
        if not self.dongle or not self.dongle.isOpen():
            self.dongle = serial.Serial(self.device, 115200)

        if not self.listener or not self.listener.isAlive():
            self.listener = self.SerialListener(self)
            self.listener.daemon = True
            self.listener.start()

    def serial_close(self):
        """Cierra la conexión serial."""
        self.dongle.close()

    def stop(self):
        """Detiene el proceso de escucha y cierra la conexión."""
        self.running = False
        self.serial_close()
