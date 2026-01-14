from fusion_solar_py.client import FusionSolarClient

# log into the API - with proper credentials...
#client = FusionSolarClient("my_user", "my_password")

# NOTE: Depending on your region, you may need to set the
# `huawei_subdomain` parameter. This is the first part of the
# URL when you enter the FusionSolar API through your webbrowser
#
client = FusionSolarClient("FOTOVOLTAICADIELCA", "DIELCAFOTOVOLTAICA5", huawei_subdomain="uni002eu5")

# get the stats
stats = client.get_power_status()

# print all stats
print(f"Energia actual: {stats.current_power_kw} kW")
print(f"Rendimiento hoy: {stats.energy_today_kwh} kWh")
print(f"Rendimiento total: {stats.energy_kwh} kWh")

# NOTE: Since an update of the API, this data does no longer seem
#       to be up-to-date. The most recent data only seems to be
#       available on th plant level (see below)

# log out - just in case
client.log_out()