import json
import os
import time
from datetime import datetime

from dotenv import load_dotenv
from fusion_solar_py.client import FusionSolarClient


def _env_int(name: str, default: int) -> int:
    v = os.getenv(name, "").strip()
    return int(v) if v.isdigit() else default


def _env_float(name: str, default: float) -> float:
    v = os.getenv(name, "").strip().replace(",", ".")
    try:
        return float(v)
    except Exception:
        return default


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _f(v, default=0.0) -> float:
    try:
        if v is None:
            return float(default)
        if isinstance(v, (int, float)):
            return float(v)
        s = str(v).strip().replace(",", ".")
        return float(s) if s else float(default)
    except Exception:
        return float(default)


def _get_nested(d: dict, *keys, default=None):
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def fetch_payload(client: FusionSolarClient, plant_index: int) -> dict:
    plant_overview = client.get_station_list() or []
    stats = client.get_power_status()

    plant_ids = client.get_plant_ids() or []
    plant_index = max(0, min(int(plant_index), len(plant_ids) - 1)) if plant_ids else 0
    plant_id = plant_ids[plant_index] if plant_ids else None

    plant_data = client.get_plant_stats(plant_id) if plant_id else {}
    last_values = client.get_last_plant_data(plant_data) or {}

    current_power_kw = _f(getattr(stats, "current_power_kw", 0))
    energy_today_kwh = _f(getattr(stats, "energy_today_kwh", 0))
    energy_total_kwh = _f(getattr(stats, "energy_kwh", 0))

    sebadal_power = 0.0
    try:
        sebadal_power = _f((plant_overview[plant_index] or {}).get("currentPower", 0))
    except Exception:
        sebadal_power = 0.0

    solar_kw = sebadal_power if sebadal_power > 0 else current_power_kw

    prod_power_val = _f(_get_nested(last_values, "productPower", "value", default=0))
    prod_power_time = _get_nested(last_values, "productPower", "time", default="") or ""

    load_kw = _f(last_values.get("totalUsePower"), 0.0)

    self_use_kw = _f(last_values.get("totalSelfUsePower"), 0.0)
    if self_use_kw <= 0 and load_kw > 0 and solar_kw > 0:
        self_use_kw = min(load_kw, solar_kw)

    buy_raw = _f(last_values.get("buyPowerRatio"), 0.0)
    if 0 < buy_raw <= 1.2:
        grid_import_kw = load_kw * max(0.0, min(buy_raw, 1.0))
    else:
        grid_import_kw = max(0.0, buy_raw)

    export_kw = 0.0
    if solar_kw > 0 and load_kw >= 0:
        export_kw = max(0.0, solar_kw - self_use_kw)

    if load_kw > 0 and grid_import_kw <= 0:
        grid_import_kw = max(0.0, load_kw - self_use_kw)

    if load_kw <= 0:
        load_kw = max(0.0, self_use_kw + grid_import_kw)

    self_use_ratio = (self_use_kw / solar_kw) if solar_kw > 0 else 0.0
    autonomy_ratio = (self_use_kw / load_kw) if load_kw > 0 else 0.0

    payload = {
        "total": {
            "potencia": round(max(0.0, current_power_kw), 3),
            "energia_hoy": round(max(0.0, energy_today_kwh), 3),
            "energia_total": round(max(0.0, energy_total_kwh), 3),
        },
        "sebadal": {
            "potencia": round(max(0.0, solar_kw), 3),
            "ultima_produccion_valor": round(max(0.0, prod_power_val), 3),
            "ultima_produccion_hora": str(prod_power_time),
            "uso_total": round(max(0.0, load_kw), 3),
            "autoconsumo": round(max(0.0, self_use_kw), 3),
            "compra_red": round(max(0.0, grid_import_kw), 3),
            "exportacion_red": round(max(0.0, export_kw), 3),
            "ratio_autoconsumo": round(max(0.0, min(self_use_ratio, 1.0)), 4),
            "ratio_autonomia": round(max(0.0, min(autonomy_ratio, 1.0)), 4),
            "bateria_kw": 0.0,
            "bateria_soc": 0.0,
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
        time.sleep(max(5, refresh))


if __name__ == "__main__":
    main()