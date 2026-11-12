
import json
import joblib
import paho.mqtt.client as mqtt

BROKER = "127.0.0.1"
PORTA = 1883

TOPICO_SENSOR = "tcc/semaforo/sensor"
TOPICO_CONTROLE = "tcc/semaforo/controle"

modelo = joblib.load("modelo_semaforo.pkl")


def ao_conectar(cliente, dados, flags, motivo, propriedades):
    print("Conectado ao Mosquitto:", motivo)
    cliente.subscribe(TOPICO_SENSOR)
    print("Aguardando dados do ESP32...")


def ao_receber(cliente, dados, mensagem):
    try:
        leitura = json.loads(mensagem.payload.decode("utf-8"))

        veiculos = float(leitura["veiculos"])
        fila = float(leitura["fila"])
        velocidade = float(leitura["velocidade_media_m_s"])

        entrada = [[veiculos, fila, velocidade]]
        tempo = float(modelo.predict(entrada)[0])

        # Limite de segurança: verde entre 3 e 12 segundos
        tempo = max(3.0, min(12.0, tempo))

        resposta = {
            "tempo_verde_s": round(tempo, 2)
        }

        cliente.publish(
            TOPICO_CONTROLE,
            json.dumps(resposta),
            qos=1
        )

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
