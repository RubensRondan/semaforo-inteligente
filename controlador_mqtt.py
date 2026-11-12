"""
Controlador MQTT do semaforo inteligente (TCC).

Recebe a leitura publicada pela ESP32, executa o modelo Random Forest,
publica o tempo de verde e REGISTRA cada ciclo em um arquivo CSV.

Configuracao por variaveis de ambiente (todas opcionais; os valores
padrao sao os mesmos do prototipo):
  MQTT_HOST, MQTT_PORT, MQTT_TOPICO_SENSOR, MQTT_TOPICO_CONTROLE,
  CAMINHO_MODELO, ARQUIVO_REGISTRO
"""
import csv
import json
import os
import time
from datetime import datetime
from pathlib import Path

import joblib
import paho.mqtt.client as mqtt

BROKER = os.environ.get("MQTT_HOST", "127.0.0.1")
PORTA = int(os.environ.get("MQTT_PORT", "1883"))

TOPICO_SENSOR = os.environ.get("MQTT_TOPICO_SENSOR", "tcc/semaforo/sensor")
TOPICO_CONTROLE = os.environ.get("MQTT_TOPICO_CONTROLE", "tcc/semaforo/controle")

CAMINHO_MODELO = os.environ.get("CAMINHO_MODELO", "modelo_semaforo.pkl")
ARQUIVO_REGISTRO = Path(os.environ.get("ARQUIVO_REGISTRO", "registro_ciclos.csv"))

CAMPOS_REGISTRO = [
    "timestamp",
    "distancia_cm",
    "veiculos",
    "fila",
    "velocidade_media_m_s",
    "tempo_verde_previsto_s",
    "tempo_processamento_ms",
]

modelo = joblib.load(CAMINHO_MODELO)


def registrar_ciclo(linha):
    """Acrescenta uma linha ao CSV (cria o arquivo com cabecalho se preciso)."""
    novo = not ARQUIVO_REGISTRO.exists()
    with ARQUIVO_REGISTRO.open("a", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=CAMPOS_REGISTRO)
        if novo:
            escritor.writeheader()
        escritor.writerow(linha)


def ao_conectar(cliente, dados, flags, motivo, propriedades):
    print("Conectado ao Mosquitto:", motivo)
    cliente.subscribe(TOPICO_SENSOR)
    print("Aguardando dados do ESP32...")


def ao_receber(cliente, dados, mensagem):
    try:
        inicio = time.perf_counter()

        leitura = json.loads(mensagem.payload.decode("utf-8"))

        veiculos = float(leitura["veiculos"])
        fila = float(leitura["fila"])
        velocidade = float(leitura["velocidade_media_m_s"])

        entrada = [[veiculos, fila, velocidade]]
        tempo = float(modelo.predict(entrada)[0])

        # Limite de seguranca: verde entre 3 e 12 segundos
        tempo = max(3.0, min(12.0, tempo))

        resposta = {
            "tempo_verde_s": round(tempo, 2)
        }

        cliente.publish(
            TOPICO_CONTROLE,
            json.dumps(resposta),
            qos=1
        )

        processamento_ms = (time.perf_counter() - inicio) * 1000.0

        registrar_ciclo({
            "timestamp": datetime.now().isoformat(timespec="milliseconds"),
            "distancia_cm": leitura.get("distancia_cm", ""),
            "veiculos": veiculos,
            "fila": fila,
            "velocidade_media_m_s": velocidade,
            "tempo_verde_previsto_s": resposta["tempo_verde_s"],
            "tempo_processamento_ms": round(processamento_ms, 2),
        })

        print("Dados recebidos:", leitura)
        print("Previsão publicada:", resposta)

    except Exception as erro:
        print("Erro ao processar mensagem:", erro)


cliente = mqtt.Client(
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    client_id="controlador_tcc"
)

cliente.on_connect = ao_conectar
cliente.on_message = ao_receber

cliente.connect(BROKER, PORTA, 60)
cliente.loop_forever()