import requests

BASE_URL = "http://172.20.10.2:5000"

print("Vehicle Quick Check")

components = requests.get(f"{BASE_URL}/components").json()
vin = requests.get(f"{BASE_URL}/components/engine/data/vin").json()
sw = requests.get(f"{BASE_URL}/components/engine/data/swversion").json()

print("Components:", components)
print("VIN:", vin)
print("SW Version:", sw)