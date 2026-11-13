
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// ==========================================
// TCC - SEMAFOROS INTELIGENTES
// ESP32 + HC-SR04 + 6 LEDs + Wi-Fi + MQTT
// ==========================================

const char* WIFI_SSID = "Rubens";
const char* WIFI_PASSWORD = "****";

// IP do computador que executa o Mosquitto
const char* MQTT_BROKER = "****";
const int MQTT_PORT = 1883;

const char* TOPICO_SENSOR = "tcc/semaforo/sensor";
const char* TOPICO_CONTROLE = "tcc/semaforo/controle";

WiFiClient conexaoWiFi;
PubSubClient mqtt(conexaoWiFi);

// VIA A
const int A_VERMELHO = 27;
const int A_AMARELO = 25;
const int A_VERDE = 26;

// VIA B
const int B_VERMELHO = 13;
const int B_AMARELO = 14;
const int B_VERDE = 32;

// HC-SR04
const int TRIG_PIN = 33;
const int ECHO_PIN = 35;

// Tempos
const unsigned long TEMPO_AMARELO = 2000;
const unsigned long TEMPO_TODOS_VERMELHOS = 1000;
const unsigned long INTERVALO_SENSOR = 300;

const unsigned long VERDE_ALTO_MS = 8000;
const unsigned long VERDE_MEDIO_MS = 5000;
const unsigned long VERDE_BAIXO_MS = 3000;
const unsigned long VERDE_PADRAO_MS = 5000;

float distanciaCm = -1.0;
unsigned long ultimaLeitura = 0;

// Tempo recebido do modelo Python
unsigned long tempoVerdeRemotoMs = 0;
bool novaPrevisaoRecebida = false;

// ==========================================
// SENSOR
// ==========================================

float medirDistancia() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(3);

  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  unsigned long duracao = pulseIn(ECHO_PIN, HIGH, 30000);

  if (duracao == 0) return -1.0;

  return (duracao * 0.0343f) / 2.0f;
}

void atualizarSensor() {
  if (millis() - ultimaLeitura >= INTERVALO_SENSOR) {
    ultimaLeitura = millis();
    distanciaCm = medirDistancia();

    Serial.print("Distancia: ");
    if (distanciaCm < 0) {
      Serial.println("sem leitura valida");
    } else {
      Serial.print(distanciaCm, 2);
      Serial.println(" cm");
    }
  }
}

// ==========================================
// CONTROLE LOCAL DE SEGURANCA
// ==========================================

unsigned long calcularTempoVerdeLocal() {
  if (distanciaCm < 0 || distanciaCm > 30.0f) {
    return VERDE_PADRAO_MS;
  }

  if (distanciaCm <= 10.0f) return VERDE_ALTO_MS;
  if (distanciaCm <= 20.0f) return VERDE_MEDIO_MS;

  return VERDE_BAIXO_MS;
}

// ==========================================
// MQTT - RECEBER PREVISAO DO PYTHON
// ==========================================

void receberMensagem(char* topico, byte* payload,
                     unsigned int tamanho) {
  if (strcmp(topico, TOPICO_CONTROLE) != 0) return;

  StaticJsonDocument<128> documento;

  DeserializationError erro =
      deserializeJson(documento, payload, tamanho);

  if (erro) {
    Serial.println("Erro no JSON recebido.");
    return;
  }

  if (documento.containsKey("tempo_verde_s")) {
    float segundos = documento["tempo_verde_s"];

    // Limite de seguranca: 3 a 12 segundos
    segundos = constrain(segundos, 3.0f, 12.0f);

    tempoVerdeRemotoMs =
        (unsigned long)(segundos * 1000.0f);

    novaPrevisaoRecebida = true;

    Serial.print("Tempo recebido do modelo: ");
    Serial.print(segundos);
    Serial.println(" segundos");
  }
}

void conectarMQTT() {
  if (WiFi.status() != WL_CONNECTED) return;
  if (mqtt.connected()) return;

  Serial.println("Conectando ao broker MQTT...");

  if (mqtt.connect("ESP32SemaforoTCC")) {
    mqtt.subscribe(TOPICO_CONTROLE);
    Serial.println("MQTT conectado e inscrito no controle.");
  } else {
    Serial.print("Falha MQTT. Codigo: ");
    Serial.println(mqtt.state());
  }
}

// ==========================================
// ENVIAR DADOS EXPERIMENTAIS AO PYTHON
// ==========================================

void publicarDadosSensor() {
  if (!mqtt.connected()) return;

  // Aproximacoes experimentais baseadas na distancia.
  // Nao representam contagens reais de veiculos.

  float veiculos;
  float fila;
  float velocidade;

  if (distanciaCm < 0 || distanciaCm > 30.0f) {
    veiculos = 0;
    fila = 0;
    velocidade = 13.9f;
  } else if (distanciaCm <= 10.0f) {
    veiculos = 5;
    fila = 5;
    velocidade = 0.0f;
  } else if (distanciaCm <= 20.0f) {
    veiculos = 3;
    fila = 2;
    velocidade = 3.0f;
  } else {
    veiculos = 1;
    fila = 0;
    velocidade = 8.0f;
  }

  StaticJsonDocument<192> documento;

  documento["distancia_cm"] = distanciaCm;
  documento["veiculos"] = veiculos;
  documento["fila"] = fila;
  documento["velocidade_media_m_s"] = velocidade;

  char mensagem[192];
  serializeJson(documento, mensagem);

  if (mqtt.publish(TOPICO_SENSOR, mensagem)) {
    Serial.print("Dados enviados ao Python: ");
    Serial.println(mensagem);
  } else {
    Serial.println("Falha ao publicar dados MQTT.");
  }
}

// ==========================================
// SOLICITAR TEMPO AO MODELO
// ==========================================

unsigned long obterTempoVerde() {
  novaPrevisaoRecebida = false;
  tempoVerdeRemotoMs = 0;

  publicarDadosSensor();

  unsigned long inicio = millis();

  // Aguarda brevemente a resposta do Python
  while (millis() - inicio < 1200) {
    mqtt.loop();

    if (novaPrevisaoRecebida) {
      return tempoVerdeRemotoMs;
    }

    delay(10);
  }

  Serial.println(
      "Sem resposta do modelo: usando controle local.");

  return calcularTempoVerdeLocal();
}

// ==========================================
// LEDS E TRANSICOES SEGURAS
// ==========================================

void apagarTodos() {
  digitalWrite(A_VERMELHO, LOW);
  digitalWrite(A_AMARELO, LOW);
  digitalWrite(A_VERDE, LOW);

  digitalWrite(B_VERMELHO, LOW);
  digitalWrite(B_AMARELO, LOW);
  digitalWrite(B_VERDE, LOW);
}

void todosVermelhos() {
  apagarTodos();
  digitalWrite(A_VERMELHO, HIGH);
  digitalWrite(B_VERMELHO, HIGH);
}

void esperarComSensor(unsigned long tempoMs) {
  unsigned long inicio = millis();

  while (millis() - inicio < tempoMs) {
    atualizarSensor();

    if (WiFi.status() == WL_CONNECTED) {
      if (!mqtt.connected()) conectarMQTT();
      mqtt.loop();
    }

    delay(5);
  }
}

// ==========================================
// FASE VIA A
// ==========================================

void faseViaA() {
  atualizarSensor();

  unsigned long tempoVerde;

  if (mqtt.connected()) {
    tempoVerde = obterTempoVerde();
  } else {
    tempoVerde = calcularTempoVerdeLocal();
    Serial.println("Controle local de contingencia.");
  }

  Serial.println("VIA A VERDE / VIA B VERMELHA");

  apagarTodos();
  digitalWrite(A_VERDE, HIGH);
  digitalWrite(B_VERMELHO, HIGH);
  esperarComSensor(tempoVerde);

  Serial.println("VIA A AMARELA / VIA B VERMELHA");

  apagarTodos();
  digitalWrite(A_AMARELO, HIGH);
  digitalWrite(B_VERMELHO, HIGH);
  esperarComSensor(TEMPO_AMARELO);

  todosVermelhos();
  esperarComSensor(TEMPO_TODOS_VERMELHOS);
}

// ==========================================
// FASE VIA B
// ==========================================

void faseViaB() {
  Serial.println("VIA B VERDE / VIA A VERMELHA");

  apagarTodos();
  digitalWrite(B_VERDE, HIGH);
  digitalWrite(A_VERMELHO, HIGH);
  esperarComSensor(VERDE_PADRAO_MS);

  Serial.println("VIA B AMARELA / VIA A VERMELHA");

  apagarTodos();
  digitalWrite(B_AMARELO, HIGH);
  digitalWrite(A_VERMELHO, HIGH);
  esperarComSensor(TEMPO_AMARELO);

  todosVermelhos();
  esperarComSensor(TEMPO_TODOS_VERMELHOS);
}

// ==========================================
// WIFI
// ==========================================

void conectarWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  Serial.print("Conectando ao Wi-Fi...");

  unsigned long inicio = millis();

  while (WiFi.status() != WL_CONNECTED &&
         millis() - inicio < 15000) {
    delay(500);
    Serial.print(".");
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWi-Fi conectado!");
    Serial.print("IP do ESP32: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\nWi-Fi indisponivel; modo local.");
  }
}

// ==========================================
// INICIALIZACAO
// ==========================================

void setup() {
  Serial.begin(115200);

  pinMode(A_VERMELHO, OUTPUT);
  pinMode(A_AMARELO, OUTPUT);
  pinMode(A_VERDE, OUTPUT);

  pinMode(B_VERMELHO, OUTPUT);
  pinMode(B_AMARELO, OUTPUT);
  pinMode(B_VERDE, OUTPUT);

  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  digitalWrite(TRIG_PIN, LOW);
  todosVermelhos();

  Serial.println("\nTCC - SEMAFOROS INTELIGENTES");

  conectarWiFi();

  mqtt.setServer(MQTT_BROKER, MQTT_PORT);
  mqtt.setCallback(receberMensagem);
  mqtt.setBufferSize(256);

  conectarMQTT();

  distanciaCm = medirDistancia();
  ultimaLeitura = millis();
}

// ==========================================
// CICLO PRINCIPAL
// ==========================================

void loop() {
  if (WiFi.status() == WL_CONNECTED) {
    if (!mqtt.connected()) conectarMQTT();
    mqtt.loop();
  }

  faseViaA();
  faseViaB();
}
