import time
from datetime import datetime
from fusion_solar_py.client import FusionSolarClient

def actualizar_html_periodicamente():
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

            actualizado = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>Monitor Solar en Tiempo Real</title>
  <style>
    html, body {{
      margin: 0;
      padding: 0;
      height: 100%;
      width: 100%;
      overflow: hidden;
      background: #f8f8f8;
      font-family: Arial, sans-serif;
    }}

    .rotated-wrapper {{
      position: absolute;
      top: -10em;
      left: 5em;
      transform: rotate(270deg) translate(-50%, -50%);
      transform-origin: center center;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 20px;
      box-sizing: border-box;
    }}

    h1 {{
      margin-bottom: 20px;
      text-align: center;
    }}

    #lastUpdate {{
      margin-bottom: 20px;
    }}

    .card-container {{
      display: flex;
      flex-direction: row;
      gap: 20px;
    }}

    .card {{
      border: 1px solid #ccc;
      padding: 20px;
      border-radius: 8px;
      min-width: 350px;
    }}

    .green {{
      background-color: #e6ffe6;
    }}

    .blue {{
      background-color: #e6f0ff;
    }}
  </style>
</head>
<body>
  <div class="rotated-wrapper">
    <h1>☀️ Monitor Solar en Tiempo Real</h1>
    <p id="lastUpdate">Última actualización: {actualizado}</p>

    <div class="card-container">
      <div class="card blue">
        <h2>🔷 Todas las plantas</h2>
        <p><strong>Potencia actual:</strong> {stats.current_power_kw} kW</p>
        <p><strong>Energía hoy:</strong> {stats.energy_today_kwh} kWh</p>
        <p><strong>Energía total:</strong> {stats.energy_kwh} kWh</p>
      </div>

      <div class="card green">
        <h2>🟢 El Sebadal</h2>
        <p><strong>Potencia actual:</strong> {plant_overview[0]['currentPower']} kW</p>
        <p><strong>Última producción:</strong> {last_values['productPower']['value']} kW a {last_values['productPower']['time']}</p>
        <p><strong>Consumo total hoy:</strong> {last_values['totalUsePower']} kWh</p>
        <p><strong>Producción total hoy:</strong> {last_values['totalProductPower']} kWh</p>
        <p><strong>Autoconsumo:</strong> {last_values['totalSelfUsePower']} kWh</p>
        <p><strong>Compra a red:</strong> {last_values['buyPowerRatio']}%</p>
      </div>
    </div>
  </div>
</body>
</html>
"""

            with open("index.html", "w", encoding="utf-8") as f:
                f.write(html)

            print(f"Archivo HTML actualizado: {actualizado}")

        except Exception as e:
            print(f"Error al actualizar HTML: {e}")

        time.sleep(60)

if __name__ == "__main__":
    actualizar_html_periodicamente()
