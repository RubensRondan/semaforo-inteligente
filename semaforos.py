import traci
import time

traci.start(["sumo-gui", "-c", "cenario.sumocfg"])

for step in range(300):
    traci.simulationStep()
    time.sleep(0.1)

traci.close()