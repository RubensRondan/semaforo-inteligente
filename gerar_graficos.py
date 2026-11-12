
import pandas as pd
import matplotlib.pyplot as plt

# Ler os dados reais coletados no SUMO
df = pd.read_csv("dados_tcc_sumo.csv")

# Ordenar os registros
df = df.sort_values(["tempo_s", "via"])

# Figura 8: tamanho das filas por via
plt.figure(figsize=(10, 5))
for via, dados in df.groupby("via"):
    plt.plot(dados["tempo_s"], dados["fila"], label=via)

plt.xlabel("Tempo de simulação (s)")
plt.ylabel("Quantidade de veículos na fila")
plt.title("Variação das filas de veículos por via")
plt.legend(fontsize=8)
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("figura_8_filas.png", dpi=300)
plt.close()

# Figura 9: quantidade de veículos por via
plt.figure(figsize=(10, 5))
for via, dados in df.groupby("via"):
    plt.plot(dados["tempo_s"], dados["veiculos"], label=via)

plt.xlabel("Tempo de simulação (s)")
plt.ylabel("Quantidade de veículos")
plt.title("Quantidade de veículos por via")
plt.legend(fontsize=8)
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("figura_9_veiculos.png", dpi=300)
plt.close()

# Figura 10: velocidade média por via
plt.figure(figsize=(10, 5))
for via, dados in df.groupby("via"):
    plt.plot(
        dados["tempo_s"],
        dados["velocidade_media_m_s"],
        label=via
    )

plt.xlabel("Tempo de simulação (s)")
plt.ylabel("Velocidade média (m/s)")
plt.title("Variação da velocidade média por via")
plt.legend(fontsize=8)
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("figura_10_velocidade.png", dpi=300)
plt.close()

print("Gráficos gerados com os dados reais do SUMO.")
