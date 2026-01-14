import threading
import time
from datetime import datetime
import json
from fusion_solar_py.client import FusionSolarClient

def actualizar_datos_periodicamente():
    while True:
        try:
            client = FusionSolarClient(
                "FOTOVOLTAICADIELCA", "DIELCAFOTOVOLTAICA5", huawei_subdomain="uni002eu5"
            )

            plant_overview = client.get_station_list()
            stats = client.get_power_status()

            plant_ids = client.get_plant_ids()
            plant_data = client.get_plant_stats(plant_ids[0])
            last_values = client.get_last_plant_data(plant_data)

            datos_json = {
                "total": {
                    "potencia": stats.current_power_kw,
                    "energia_hoy": stats.energy_today_kwh,
                    "energia_total": stats.energy_kwh
                },
                "sebadal": {
                    "potencia": plant_overview[0]['currentPower'],
                    "ultima_produccion_valor": last_values['productPower']['value'],
                    "ultima_produccion_hora": last_values['productPower']['time'],
                    "uso_total": last_values['totalUsePower'],
                    "produccion_total": last_values['totalProductPower'],
                    "autoconsumo": last_values['totalSelfUsePower'],
                    "compra_red": last_values['buyPowerRatio']
                },
                "actualizado": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            with open("datos.json", "w") as f:
                json.dump(datos_json, f, indent=4)

            print(f"Datos actualizados a las {datos_json['actualizado']}")

        except Exception as e:
            print(f"Error al actualizar datos: {e}")

        time.sleep(60)  

if __name__ == "__main__":
    actualizar_datos_periodicamente()
