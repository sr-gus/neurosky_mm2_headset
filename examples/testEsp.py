from machine import Pin, PWM
from time import sleep

# Configuración del pin y PWM
led = PWM(Pin(13), freq=1000)  # Configura el pin 13 para PWM a 1 kHz

# Función para hacer un barrido de ciclo de trabajo
def barrido_pwm():
    # Incrementa el ciclo de trabajo de 0 a 1023
    for duty in range(0, 1024, 10):  # Ajusta el incremento si lo necesitas más suave
        led.duty(duty)
        sleep(0.01)  # Tiempo de espera para observar el cambio

    # Decrementa el ciclo de trabajo de 1023 a 0
    for duty in range(1023, -1, -10):
        led.duty(duty)
        sleep(0.01)

# Loop principal
while True:
    barrido_pwm()
