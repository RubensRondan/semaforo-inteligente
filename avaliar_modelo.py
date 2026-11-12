"""
Avaliacao complementar do modelo (Secao 4 do Guia do Usuario).

Rode na mesma pasta de treinar_modelo.py, DEPOIS de treina-lo:
    python avaliar_modelo.py

Gera: distribuicao dos tempos de referencia, MAE e RMSE no teste (mesma
divisao 80/20 do treino), validacao cruzada de 5 folds e a conferencia
do modelo com os 4 estados que o firmware da ESP32 realmente envia.
"""
import csv
from collections import Counter
from pathlib import Path

import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import KFold, cross_val_score, train_test_split

ARQUIVO_TREINO = Path("dados_treinamento.csv")
ARQUIVO_MODELO = Path("modelo_semaforo.pkl")


def definir_tempo_verde(veiculos, fila, velocidade):
    # Mesma regra de referencia do treinar_modelo.py
    if fila >= 3:
        return 12
    if fila >= 1:
        return 9
    if veiculos >= 3 and velocidade < 5:
        return 8
    if veiculos >= 3:
        return 7
    if veiculos >= 1:
        return 6
    return 5


def novo_modelo():
    return RandomForestRegressor(
        n_estimators=100, max_depth=8, random_state=42, n_jobs=-1
    )


with ARQUIVO_TREINO.open("r", encoding="utf-8", newline="") as arquivo:
    linhas = list(csv.DictReader(arquivo))

X = [[float(l["veiculos"]), float(l["fila"]), float(l["velocidade_media_m_s"])]
     for l in linhas]
y = [float(l["tempo_verde_referencia_s"]) for l in linhas]

print(f"Registros: {len(X)}")

print("\n1) Distribuicao dos tempos de referencia (s):")
for tempo, qtd in sorted(Counter(y).items()):
    print(f"   {tempo:>4.0f} s: {qtd:>4} registros ({100 * qtd / len(y):.1f}%)")

X_treino, X_teste, y_treino, y_teste = train_test_split(
    X, y, test_size=0.20, random_state=42
)
modelo_teste = novo_modelo().fit(X_treino, y_treino)
previsoes = modelo_teste.predict(X_teste)
print("\n2) Conjunto de teste (80/20, random_state=42):")
print(f"   MAE : {mean_absolute_error(y_teste, previsoes):.3f} s")
print(f"   RMSE: {mean_squared_error(y_teste, previsoes) ** 0.5:.3f} s")

cv = KFold(n_splits=5, shuffle=True, random_state=42)
mae = -cross_val_score(novo_modelo(), X, y, cv=cv,
                       scoring="neg_mean_absolute_error")
rmse = -cross_val_score(novo_modelo(), X, y, cv=cv,
                        scoring="neg_root_mean_squared_error")
print("\n3) Validacao cruzada (5 folds, com sorteio):")
print(f"   MAE : {mae.mean():.3f} +/- {mae.std():.3f} s")
print(f"   RMSE: {rmse.mean():.3f} +/- {rmse.std():.3f} s")

print("\n4) Os 4 estados que o firmware da ESP32 envia ao modelo:")
modelo = joblib.load(ARQUIVO_MODELO)
estados = [
    ("sem leitura ou acima de 30 cm", [0, 0, 13.9]),
    ("de 20 a 30 cm", [1, 0, 8.0]),
    ("de 10 a 20 cm", [3, 2, 3.0]),
    ("ate 10 cm", [5, 5, 0.0]),
]
for nome, entrada in estados:
    referencia = definir_tempo_verde(*entrada)
    previsto = float(modelo.predict([entrada])[0])
    previsto = max(3.0, min(12.0, previsto))
    print(f"   {nome:<32} entrada={entrada} | regra={referencia} s | "
          f"modelo={previsto:.2f} s")