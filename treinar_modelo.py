
import csv
from pathlib import Path

import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split

ARQUIVO_DADOS = Path("dados_tcc_sumo.csv")
ARQUIVO_MODELO = Path("modelo_semaforo.pkl")
ARQUIVO_TREINO = Path("dados_treinamento.csv")

# 1. Ler os dados coletados pelo SUMO
with ARQUIVO_DADOS.open("r", encoding="utf-8", newline="") as arquivo:
    dados = list(csv.DictReader(arquivo))

if not dados:
    raise ValueError("O CSV está vazio.")

# 2. Definir uma política de referência explícita.
# O alvo é uma regra experimental, NÃO um tempo ótimo comprovado.
def definir_tempo_verde(veiculos, fila, velocidade):
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

# 3. Preparar atributos e tempos-alvo
X = []
y = []

for registro in dados:
    veiculos = float(registro["veiculos"])
    fila = float(registro["fila"])
    velocidade = float(registro["velocidade_media_m_s"])

    X.append([veiculos, fila, velocidade])
    y.append(definir_tempo_verde(veiculos, fila, velocidade))

# Guardar os dados com os alvos usados no treinamento
with ARQUIVO_TREINO.open("w", encoding="utf-8", newline="") as arquivo:
    campos = [
        "veiculos",
        "fila",
        "velocidade_media_m_s",
        "tempo_verde_referencia_s",
    ]
    escritor = csv.DictWriter(arquivo, fieldnames=campos)
    escritor.writeheader()

    for atributos, alvo in zip(X, y):
        escritor.writerow({
            "veiculos": atributos[0],
            "fila": atributos[1],
            "velocidade_media_m_s": atributos[2],
            "tempo_verde_referencia_s": alvo,
        })

# 4. Separar treino e teste
X_treino, X_teste, y_treino, y_teste = train_test_split(
    X, y, test_size=0.20, random_state=42
)

# 5. Treinar o Random Forest
modelo = RandomForestRegressor(
    n_estimators=100,
    max_depth=8,
    random_state=42,
    n_jobs=-1,
)
modelo.fit(X_treino, y_treino)

# 6. Avaliar as previsões no conjunto de teste
previsoes = modelo.predict(X_teste)
erro_medio = mean_absolute_error(y_teste, previsoes)

# 7. Salvar o modelo treinado
joblib.dump(modelo, ARQUIVO_MODELO)

print("Treinamento concluído.")
print(f"Registros totais: {len(dados)}")
print(f"Registros de treino: {len(X_treino)}")
print(f"Registros de teste: {len(X_teste)}")
print(f"MAE no teste: {erro_medio:.3f} segundos")
print(f"Modelo salvo em: {ARQUIVO_MODELO}")
print(f"Dados com alvos salvos em: {ARQUIVO_TREINO}")

print("\nExemplos de previsão:")
for atributos, real, previsto in list(zip(X_teste, y_teste, previsoes))[:5]:
    print(
        f"Veículos={atributos[0]:.0f}, "
        f"fila={atributos[1]:.0f}, "
        f"velocidade={atributos[2]:.2f} m/s | "
        f"referência={real}s | "
        f"modelo={previsto:.2f}s"
    )
