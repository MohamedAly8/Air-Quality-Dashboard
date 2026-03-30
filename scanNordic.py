import asyncio
from bleak import BleakScanner

THINGY_SERVICE = "ef680100-9b35-4933-9b10-52ffa9740042"

async def main():
    print("Scanning for Thingy:52 (10 seconds)...\n")
    devices = await BleakScanner.discover(timeout=10.0, return_adv=True)
    
    found = False
    for address, (device, adv) in devices.items():
        uuids = [str(u).lower() for u in adv.service_uuids]
        if any(THINGY_SERVICE in u for u in uuids):
            print(f"  Found Thingy:52!")
            print(f"  Name:    {device.name}")
            print(f"  Address: {device.address}")
            found = True
    
    if not found:
        print("Thingy:52 not found. Try these:")
        print("  1. Press the button on the Thingy:52 to wake it up")
        print("  2. Make sure it's charged")
        print("  3. Check System Settings > Privacy > Bluetooth — allow Terminal")

asyncio.run(main())