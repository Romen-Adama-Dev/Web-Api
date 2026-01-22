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

def _f(v, default=0.0) -> float:
    """Convierte cualquier valor a float de forma segura"""
    try:
        if v is None:
            return float(default)
        if isinstance(v, (int, float)):
            return float(v)
        s = str(v).strip().replace(",", ".")
        return float(s) if s else float(default)
    except:
        return float(default)

def _get_nested(d: dict, *keys, default=None):
    """Obtiene valores anidados de forma segura"""
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur

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
        
        # Obtener todos los datos disponibles
        print(f"📊 Obteniendo datos...")
        plant_overview = client.get_station_list() or []
        stats = client.get_power_status()
        plant_ids = client.get_plant_ids() or []
        
        if not plant_ids:
            raise Exception("No se encontraron plantas")
        
        plant_id = plant_ids[plant_index]
        plant_data = client.get_plant_stats(plant_id)
        last_values = client.get_last_plant_data(plant_data) or {}
        
        # Datos básicos
        current_power_kw = _f(getattr(stats, "current_power_kw", 0))
        energy_today_kwh = _f(getattr(stats, "energy_today_kwh", 0))
        energy_total_kwh = _f(getattr(stats, "energy_kwh", 0))
        
        # Potencia solar
        sebadal_power = _f((plant_overview[plant_index] or {}).get("currentPower", 0))
        solar_kw = sebadal_power if sebadal_power > 0 else current_power_kw
        
        # Datos de producción
        prod_power_val = _f(_get_nested(last_values, "productPower", "value"), 0)
        prod_power_time = _get_nested(last_values, "productPower", "time", default="") or ""
        
        # CARGA/CONSUMO TOTAL (lo que falta)
        load_kw = _f(last_values.get("totalUsePower"), 0.0)
        
        # AUTOCONSUMO (energía solar usada directamente)
        self_use_kw = _f(last_values.get("totalSelfUsePower"), 0.0)
        
        # Si no hay autoconsumo reportado pero hay solar y carga, calcularlo
        if self_use_kw <= 0 and load_kw > 0 and solar_kw > 0:
            self_use_kw = min(load_kw, solar_kw)
        
        # COMPRA DE RED (lo que falta de energía)
        buy_raw = _f(last_values.get("buyPowerRatio"), 0.0)
        
        # Si buyPowerRatio está entre 0-1.2, es un ratio (porcentaje)
        if 0 < buy_raw <= 1.2:
            grid_import_kw = load_kw * max(0.0, min(buy_raw, 1.0))
        else:
            # Si es mayor, es valor absoluto en kW
            grid_import_kw = max(0.0, buy_raw)
        
        # EXPORTACIÓN A RED (excedente solar)
        export_kw = 0.0
        if solar_kw > 0 and load_kw >= 0:
            export_kw = max(0.0, solar_kw - self_use_kw)
        
        # Ajuste: si no hay compra de red detectada pero la carga es mayor que autoconsumo
        if load_kw > 0 and grid_import_kw <= 0:
            grid_import_kw = max(0.0, load_kw - self_use_kw)
        
        # Ajuste: si load_kw está en 0 pero tenemos autoconsumo + compra red
        if load_kw <= 0:
            load_kw = max(0.0, self_use_kw + grid_import_kw)
        
        # BATERÍA (si existe)
        battery_kw = _f(last_values.get("chargeDischargePower"), 0.0)
        battery_soc = _f(last_values.get("batterySoc"), 0.0)
        
        # Ratios útiles
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
                
                # Datos corregidos
                "uso_total": round(max(0.0, load_kw), 3),
                "autoconsumo": round(max(0.0, self_use_kw), 3),
                "compra_red": round(max(0.0, grid_import_kw), 3),
                "exportacion_red": round(max(0.0, export_kw), 3),
                
                # Batería
                "bateria_kw": round(battery_kw, 3),
                "bateria_soc": round(max(0.0, min(battery_soc, 100.0)), 1),
                
                # Ratios
                "ratio_autoconsumo": round(max(0.0, min(self_use_ratio, 1.0)), 4),
                "ratio_autonomia": round(max(0.0, min(autonomy_ratio, 1.0)), 4),
            },
            "actualizado": _now(),
        }
        
        # Debug: mostrar todos los datos crudos disponibles
        print(f"📋 Datos crudos disponibles:")
        for key, value in last_values.items():
            print(f"   {key}: {value}")
        
        print(f"\n✅ Procesado:")
        print(f"   Solar: {solar_kw:.3f} kW")
        print(f"   Carga: {load_kw:.3f} kW")
        print(f"   Autoconsumo: {self_use_kw:.3f} kW")
        print(f"   Compra red: {grid_import_kw:.3f} kW")
        print(f"   Exportación: {export_kw:.3f} kW")
        print(f"   Batería: {battery_kw:.3f} kW ({battery_soc:.1f}%)")
        
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=4, ensure_ascii=False)
        
        print(f"\n✅ Actualizado: {payload['actualizado']}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        if client:
            try:
                client.log_out()
            except:
                pass

if __name__ == "__main__":
    main()