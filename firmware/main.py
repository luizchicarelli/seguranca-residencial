# Sensores para a Segurança Residencial — ESP32 + sensor Hall (simulado) no Wokwi, em MicroPython
#
# O Wokwi não tem sensor Hall, então um slide potentiometer no GPIO34 faz o papel
# de um sensor Hall linear (tipo SS49E), cuja saída é uma tensão proporcional ao campo:
#   slider no máximo (3,3 V)  = ímã encostado = ~118 mT = porta FECHADA
#   slider no meio ou abaixo = ímã longe     = ~0 mT   = porta ABERTA
import json
import time

import network
from machine import ADC, Pin

try:
    import requests
except ImportError:
    import urequests as requests

# ---- Configuração: no GitHub ficam só os placeholders; valores reais só no Wokwi ----
API_URL = "https://SEU-PROJETO.supabase.co/functions/v1/readings"
DEVICE_KEY = "COLOQUE_A_DEVICE_KEY_AQUI"
DEVICE_ID = "porta-01"

# Modelo do sensor: V = V_ZERO + SENS * B. Calibrar se trocar o sensor.
V_ZERO = 1.65          # saída com campo zero (Vcc/2)
SENS_V_PER_MT = 0.014  # 14 mV/mT (~1,4 mV/G do SS49E)

# Histerese: evita oscilar entre aberta/fechada perto do limite.
CLOSE_MT = 30.0  # acima disso: fechada
OPEN_MT = 20.0   # abaixo disso: aberta

SAMPLE_MS = 1000       # intervalo de coleta
SEND_MS = 5000         # envio periódico (heartbeat)
ALERT_OPEN_MS = 10000  # aberta por mais que isso = alerta

hall = ADC(Pin(34))         # ADC1 (o ADC2 não funciona com o Wi-Fi ligado)
hall.atten(ADC.ATTN_11DB)   # faixa de entrada de 0 a ~3,3 V
led = Pin(26, Pin.OUT)      # LED vermelho de alerta


def read_millitesla():
    # Média de 8 amostras para reduzir ruído. O ADC é de 12 bits;
    # read_u16() apenas reescala o resultado para 0–65535.
    avg = sum(hall.read_u16() for _ in range(8)) / 8
    volts = avg * 3.3 / 65535
    mt = (volts - V_ZERO) / SENS_V_PER_MT
    return max(0.0, mt)  # negativo = ímã longe (ou polo invertido)


def send_reading(mt, closed, alert):
    body = json.dumps({
        "device_id": DEVICE_ID,
        "metric": "magnetic_field",
        "value": round(mt, 1),
        "unit": "mT",
        "state": "closed" if closed else "open",
        "alert": alert,
    })
    try:
        r = requests.post(API_URL, data=body, headers={
            "Content-Type": "application/json",
            "x-device-key": DEVICE_KEY,
        })
        code = r.status_code
        r.close()
    except OSError as e:  # sem rede, DNS ou TLS falhou: tenta de novo na próxima coleta
        print("Erro de rede:", e)
        code = -1
    print("POST", code, body)
    return code == 201


wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect("Wokwi-GUEST", "")
print("Conectando ao Wi-Fi", end="")
while not wifi.isconnected():
    print(".", end="")
    time.sleep(0.25)
print(" conectado")

closed = True
opened_at = 0
last_send = 0
sent_once, sent_closed, sent_alert = False, True, False

while True:
    mt = read_millitesla()
    now = time.ticks_ms()

    if closed and mt < OPEN_MT:
        closed, opened_at = False, now
    elif not closed and mt > CLOSE_MT:
        closed = True
    alert = (not closed) and time.ticks_diff(now, opened_at) > ALERT_OPEN_MS
    led.value(alert)

    print("B = {:.1f} mT  {}{}".format(mt, "FECHADA" if closed else "ABERTA", "  ALERTA" if alert else ""))

    # Envia na mudança de estado (resposta imediata) ou a cada SEND_MS (heartbeat).
    # Se o envio falhar, tenta de novo na próxima coleta.
    changed = (not sent_once) or closed != sent_closed or alert != sent_alert
    if changed or time.ticks_diff(now, last_send) >= SEND_MS:
        last_send = now
        if send_reading(mt, closed, alert):
            sent_once, sent_closed, sent_alert = True, closed, alert

    time.sleep_ms(SAMPLE_MS)
