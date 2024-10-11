const int ledPin = 13; // Pin donde está conectado el LED
const int pwmChannel = 0;  // Canal PWM que usará la ESP32
const int pwmFreq = 5000;  // Frecuencia PWM en Hz
const int pwmResolution = 8;  // Resolución de 8 bits (0-255)

// Límites para el ciclo de trabajo
const float minValue = 0.0;  // Valor mínimo del flotante
const float maxValue = 100.0;  // Valor máximo del flotante

void setup() {
  Serial.begin(115200);
  
  // Configurar el pin como salida
  ledcSetup(pwmChannel, pwmFreq, pwmResolution);
  ledcAttachPin(ledPin, pwmChannel);
  
  // Inicializar el LED apagado
  ledcWrite(pwmChannel, 0);
}

void loop() {
  if (Serial.available() > 0) {
    // Leer el valor flotante
    String input = Serial.readStringUntil('\n');
    input.trim();  // Eliminar espacios y saltos de línea
    float value = input.toFloat();

    // Limitar el valor al rango especificado
    if (value < minValue) {
      value = minValue;
    } else if (value > maxValue) {
      value = maxValue;
    }

    // Mapear el valor al rango de 0 a 255 para el ciclo de trabajo del PWM
    int dutyCycle = map(value * 100, minValue * 100, maxValue * 100, 0, 255);

    // Ajustar el ciclo de trabajo del PWM
    ledcWrite(pwmChannel, dutyCycle);
    Serial.print("Valor recibido: ");
    Serial.print(value);
    Serial.print(" - Ciclo de trabajo PWM: ");
    Serial.println(dutyCycle);
  }
}
