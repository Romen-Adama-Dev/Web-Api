import json
import os
from datetime import datetime
from dotenv import load_dotenv
from fusion_solar_py.client import FusionSolarClient

def _env_int(name: str, default: int) -> int:
    v = os.getenv(name, "").strip()
    return int(v) if v.isdigit() else default

def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def main() -> None:
    load_dotenv()
    
    user = os.getenv("FUSION_USER", "").strip()
    pwd = os.getenv("FUSION_PASS", "").strip()
    sub = os.getenv("FUSION_SUBDOMAIN", "").strip()
    plant_index = _env_int("PLANT_INDEX", 0)
    out_file = os.getenv("OUT_FILE", "datos.json").strip() or "datos.json"
    
    if not user or not pwd or not sub:
        raise SystemExit("❌ Faltan variables de entorno")
    
    client = None
    try:
        print(f"🔌 Conectando a FusionSolar ({sub})...")
        client = FusionSolarClient(user, pwd, huawei_subdomain=sub)
        
        print(f"📊 Obteniendo datos de planta {plant_index}...")
        plant_overview = client.get_station_list()
        stats = client.get_power_status()
        plant_ids = client.get_plant_ids()
        plant_id = plant_ids[plant_index]
        plant_data = client.get_plant_stats(plant_id)
        last_values = client.get_last_plant_data(plant_data)
        sebadal_power = plant_overview[plant_index].get("currentPower", 0)
        
        payload = {
            "total": {
                "potencia": float(stats.current_power_kw or 0),
                "energia_hoy": float(stats.energy_today_kwh or 0),
                "energia_total": float(stats.energy_kwh or 0),
            },
            "sebadal": {
                "potencia": str(sebadal_power),
                "ultima_produccion_valor": float(last_values["productPower"]["value"] or 0),
                "ultima_produccion_hora": str(last_values["productPower"]["time"] or ""),
                "uso_total": float(last_values.get("totalUsePower") or 0),
                "produccion_total": float(last_values.get("totalProductPower") or 0),
                "autoconsumo": float(last_values.get("totalSelfUsePower") or 0),
                "compra_red": float(last_values.get("buyPowerRatio") or 0),
            },
            "actualizado": _now(),
        }
        
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=4, ensure_ascii=False)
        
        print(f"✅ Actualizado: {payload['actualizado']}")
        print(f"   Solar: {payload['total']['potencia']} kW")
        print(f"   Energía hoy: {payload['total']['energia_hoy']} kWh")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    finally:
        if client:
            try:
                client.log_out()
            except:
                pass

if __name__ == "__main__":
    main()