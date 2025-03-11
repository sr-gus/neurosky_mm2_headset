#include <Arduino.h>

// Pines para cada LED (activos a tierra)
const int redPin    = 25;  // LED rojo
const int orangePin = 33;  // LED naranja
const int yellowPin = 32;  // LED amarillo
const int greenPin  = 19;  // LED verde
const int bluePin   = 21;  // LED azul

// Frecuencia y resolución para PWM
const int pwmFreq = 5000;
const int pwmRes  = 8;  // 0-255

// Función para mapear la meditación a un valor PWM (255..0)
int computeLedPwm(float meditation, float rangeStart, float rangeEnd) {
  // Si está por debajo del rango, LED apagado (255)
  if (meditation < rangeStart) {
    return 255;
  }
  // Si está por encima (o igual) al final del rango, LED encendido (0)
  else if (meditation >= rangeEnd) {
    return 0;
  }
  // Si está dentro del rango, calculamos parcial (255..0)
  else {
    return map(meditation, rangeStart, rangeEnd, 255, 0);
  }
}

void setup() {
  Serial.begin(115200);

  // Con la nueva API LEDC (versión 3.0+ de Arduino-ESP32),
  // "ledcAttach(pin, freq, resolution)" configura y asigna automáticamente un canal.
  ledcAttach(redPin,    pwmFreq, pwmRes);
  ledcAttach(orangePin, pwmFreq, pwmRes);
  ledcAttach(yellowPin, pwmFreq, pwmRes);
  ledcAttach(greenPin,  pwmFreq, pwmRes);
  ledcAttach(bluePin,   pwmFreq, pwmRes);

  // Apagamos todos al inicio (255 = apagado, 0 = encendido)
  ledcWrite(redPin,    255);
  ledcWrite(orangePin, 255);
  ledcWrite(yellowPin, 255);
  ledcWrite(greenPin,  255);
  ledcWrite(bluePin,   255);
}

void loop() {
  // Verificamos si llegó un valor por Serial
  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n');
    input.trim();

    // Convertimos a flotante el valor de meditación
    float meditationValue = input.toFloat();

    // Forzamos el rango 0-100 por si llegan valores fuera de rango
    if (meditationValue < 0)   meditationValue = 0;
    if (meditationValue > 100) meditationValue = 100;

    // Calculamos el PWM para cada LED en función de la meditación
    int redPwm    = computeLedPwm(meditationValue, 0, 20);
    int orangePwm = computeLedPwm(meditationValue, 20, 40);
    int yellowPwm = computeLedPwm(meditationValue, 40, 60);
    int greenPwm  = computeLedPwm(meditationValue, 60, 80);
    int bluePwm   = computeLedPwm(meditationValue, 80, 100);

    // Escribimos cada valor PWM
    ledcWrite(redPin,    redPwm);
    ledcWrite(orangePin, orangePwm);
    ledcWrite(yellowPin, yellowPwm);
    ledcWrite(greenPin,  greenPwm);
    ledcWrite(bluePin,   bluePwm);
  }
}
