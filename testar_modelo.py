
import joblib

modelo = joblib.load("modelo_semaforo.pkl")

casos = [
    [0, 0, 13.9],
    [2, 1, 5.0],
    [5, 5, 0.0],
]

for veiculos, fila, velocidade in casos:
    entrada = [[veiculos, fila, velocidade]]
    tempo = modelo.predict(entrada)[0]

    print(
        f"Veículos: {veiculos} | "
        f"Fila: {fila} | "
        f"Velocidade: {velocidade:.2f} m/s | "
        f"Verde previsto: {tempo:.2f} segundos"
    )
