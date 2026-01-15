import json
import os
import time
from datetime import datetime

from dotenv import load_dotenv
from fusion_solar_py.client import FusionSolarClient


def _env_int(name: str, default: int) -> int:
    v = os.getenv(name, "").strip()
    return int(v) if v.isdigit() else default


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def fetch_payload(client: FusionSolarClient, plant_index: int) -> dict:
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

    return payload


def write_json(path: str, payload: dict) -> None:
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=4, ensure_ascii=False)
    os.replace(tmp_path, path)


def main() -> None:
    load_dotenv()

    user = os.getenv("FUSION_USER", "").strip()
    pwd = os.getenv("FUSION_PASS", "").strip()
    sub = os.getenv("FUSION_SUBDOMAIN", "").strip()

    refresh = _env_int("REFRESH_SECONDS", 60)
    plant_index = _env_int("PLANT_INDEX", 0)
    out_file = os.getenv("OUT_FILE", "datos.json").strip() or "datos.json"

    if not user or not pwd or not sub:
        raise SystemExit("Faltan variables de entorno: FUSION_USER, FUSION_PASS, FUSION_SUBDOMAIN")

    while True:
        client = None
        try:
            client = FusionSolarClient(user, pwd, huawei_subdomain=sub)
            payload = fetch_payload(client, plant_index)
            write_json(out_file, payload)
            print(f"OK {payload['actualizado']}")
        except Exception as e:
            print(f"ERROR {_now()} {e}")
        finally:
            try:
                if client:
                    client.log_out()
            except Exception:
                pass

        time.sleep(refresh)


if __name__ == "__main__":
    main()
