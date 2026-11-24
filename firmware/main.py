# Sensores para a Segurança Residencial — ESP32 no Wokwi, em MicroPython
#
# 3 sensores Hall (porta e 2 janelas) + 1 sensor de presença PIR.
# O Wokwi não tem sensor Hall: cada slide potentiometer faz o papel de um Hall linear
# (tipo SS49E), cuja saída é uma tensão proporcional ao campo do ímã:
#   slider no máximo (3,3 V)  = ímã encostado = ~118 mT = FECHADA
#   slider no meio ou abaixo = ímã longe     = ~0 mT   = ABERTA
# O alarme é armado/desarmado pelo painel; o ESP32 recebe o estado na resposta de cada envio.
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

# Sensores Hall: (device_id, pino do ADC1). O ADC2 não funciona com o Wi-Fi ligado.
HALL_SENSORS = [
    ("porta-entrada", 34),
    ("janela-sala", 35),
    ("janela-quarto", 32),
]
PIR_ID, PIR_PIN = "presenca-sala", 27

# Modelo do sensor Hall: V = V_ZERO + SENS * B. Calibrar se trocar o sensor.
V_ZERO = 1.65          # saída com campo zero (Vcc/2)
SENS_V_PER_MT = 0.014  # 14 mV/mT (~1,4 mV/G do SS49E)

# Histerese: evita oscilar entre aberta/fechada perto do limite.
CLOSE_MT = 30.0  # acima disso: fechada
OPEN_MT = 20.0   # abaixo disso: aberta

SAMPLE_MS = 1000       # intervalo de coleta
SEND_MS = 5000         # envio periódico (heartbeat)
ALERT_OPEN_MS = 10000  # desarmado: aberta por mais que isso = alerta

led_alert = Pin(26, Pin.OUT)  # vermelho: alerta / intrusão
led_armed = Pin(25, Pin.OUT)  # amarelo: alarme armado
pir = Pin(PIR_PIN, Pin.IN)    # sinal digital: 1 = movimento

halls = []
for device_id, pin in HALL_SENSORS:
    adc = ADC(Pin(pin))
    adc.atten(ADC.ATTN_11DB)  # faixa de entrada de 0 a ~3,3 V
    halls.append({"id": device_id, "adc": adc, "closed": True, "opened_at": 0, "mt": 0.0, "alert": False})


def read_millitesla(adc):
    # Média de 8 amostras para reduzir ruído. O ADC é de 12 bits;
    # read_u16() apenas reescala o resultado para 0–65535.
    avg = sum(adc.read_u16() for _ in range(8)) / 8
    volts = avg * 3.3 / 65535
    mt = (volts - V_ZERO) / SENS_V_PER_MT
    return max(0.0, mt)  # negativo = ímã longe (ou polo invertido)


def send_batch(batch):
    """Envia todas as leituras em UM POST (um único handshake TLS).
    Devolve o estado do alarme informado pela API, ou None se o envio falhou."""
    body = json.dumps(batch)
    try:
        r = requests.post(API_URL, data=body, headers={
            "Content-Type": "application/json",
            "x-device-key": DEVICE_KEY,
        })
        code = r.status_code
        armed = r.json().get("armed") if code == 201 else None
        r.close()
    except (OSError, ValueError) as e:  # sem rede, TLS ou resposta inválida: tenta na próxima coleta
        print("Erro no envio:", e)
        code, armed = -1, None
    print("POST", code, "-", len(batch), "leituras")
    return armed


wifi = network.WLAN(network.STA_IF)
wifi.active(True)
print("Conectando ao Wi-Fi", end="")
while not wifi.isconnected():
    wifi.connect("Wokwi-GUEST", "")
    for _ in range(40):  # espera até 10 s; se não conectar, tenta de novo
        if wifi.isconnected():
            break
        print(".", end="")
        time.sleep(0.25)
    else:
        print(" sem resposta, tentando de novo", end="")
        wifi.disconnect()
print(" conectado")

armed = False      # atualizado a cada resposta da API
last_send = 0
last_sent = None   # "assinatura" dos estados enviados por último

while True:
    now = time.ticks_ms()

    # 1) Sensores Hall: conversão, histerese e regra de alerta
    for h in halls:
        h["mt"] = read_millitesla(h["adc"])
        if h["closed"] and h["mt"] < OPEN_MT:
            h["closed"], h["opened_at"] = False, now
        elif not h["closed"] and h["mt"] > CLOSE_MT:
            h["closed"] = True
        is_open = not h["closed"]
        # Armado: qualquer abertura é intrusão. Desarmado: só se ficar aberta tempo demais.
        h["alert"] = is_open and (armed or time.ticks_diff(now, h["opened_at"]) > ALERT_OPEN_MS)

    # 2) Sensor de presença: leitura digital direta do GPIO
    motion = pir.value() == 1
    pir_alert = armed and motion

    any_alert = pir_alert or any(h["alert"] for h in halls)
    led_alert.value(any_alert)
    led_armed.value(armed)

    print("{} | {} | presença: {}{}".format(
        "ARMADO" if armed else "desarmado",
        " ".join("{}={:.0f}mT/{}".format(h["id"], h["mt"], "F" if h["closed"] else "A") for h in halls),
        "SIM" if motion else "não",
        "  >>> ALERTA" if any_alert else ""))

    # 3) Envia em lote na mudança de qualquer estado (resposta imediata) ou a cada SEND_MS
    signature = tuple((h["closed"], h["alert"]) for h in halls) + (motion, pir_alert)
    if signature != last_sent or time.ticks_diff(now, last_send) >= SEND_MS:
        last_send = now
        batch = [{
            "device_id": h["id"], "metric": "magnetic_field", "value": round(h["mt"], 1),
            "unit": "mT", "state": "closed" if h["closed"] else "open", "alert": h["alert"],
        } for h in halls]
        batch.append({
            "device_id": PIR_ID, "metric": "presence", "value": 1 if motion else 0,
            "unit": "bool", "state": "motion" if motion else "clear", "alert": pir_alert,
        })
        result = send_batch(batch)
        if result is not None:
            last_sent = signature
            armed = bool(result)

    time.sleep_ms(SAMPLE_MS)
