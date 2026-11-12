
import csv
import os
import sys

# Localiza a instalacao do SUMO
if "SUMO_HOME" not in os.environ:
    candidatos = [
        r"C:\Program Files (x86)\Eclipse\Sumo",
        r"C:\Program Files\Eclipse\Sumo",
    ]
    for pasta in candidatos:
        if os.path.isdir(os.path.join(pasta, "tools")):
            os.environ["SUMO_HOME"] = pasta
            break

if "SUMO_HOME" not in os.environ:
    raise RuntimeError(
        "SUMO_HOME nao encontrado. Verifique a instalacao do SUMO."
    )

sys.path.append(os.path.join(os.environ["SUMO_HOME"], "tools"))
import traci

CONFIG = "cenario.sumocfg"
ARQUIVO_SAIDA = "dados_tcc_sumo.csv"
DURACAO = 100

try:
    traci.start([
        "sumo",
        "-c", CONFIG,
        "--end", str(DURACAO),
        "--no-step-log", "true",
    ])

    # Identifica as vias validas existentes na rede carregada.
    vias = list(traci.edge.getIDList())
    vias = [
        via for via in vias
        if not via.startswith(":")
    ]

    print("\nVias identificadas na simulacao:")
    for via in vias:
        print("-", via)

    if not vias:
        raise RuntimeError("Nenhuma via valida foi encontrada.")

    with open(
        ARQUIVO_SAIDA,
        "w",
        newline="",
        encoding="utf-8"
    ) as arquivo:
        campos = [
            "tempo_s",
            "via",
            "veiculos",
            "fila",
            "velocidade_media_m_s",
        ]
        escritor = csv.DictWriter(
            arquivo,
            fieldnames=campos
        )
        escritor.writeheader()

        while traci.simulation.getMinExpectedNumber() > 0:
            traci.simulationStep()
            tempo = traci.simulation.getTime()

            for via in vias:
                veiculos = traci.edge.getLastStepVehicleNumber(via)
                fila = traci.edge.getLastStepHaltingNumber(via)
                velocidade = traci.edge.getLastStepMeanSpeed(via)

                escritor.writerow({
                    "tempo_s": tempo,
                    "via": via,
                    "veiculos": veiculos,
                    "fila": fila,
                    "velocidade_media_m_s": round(velocidade, 3),
                })

    print(f"\nColeta concluida: {ARQUIVO_SAIDA}")

finally:
    if traci.isLoaded():
        traci.close()
