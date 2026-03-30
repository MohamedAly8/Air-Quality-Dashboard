import asyncio
import struct
from bleak import BleakClient

THINGY_ADDRESS  = "D7BD6C56-3226-E270-5080-C60DFB8E5A28"
ENV_CONFIG_UUID = "ef680206-9b35-4933-9b10-52ffa9740042"

async def main():
    async with BleakClient(THINGY_ADDRESS) as client:
        data = await client.read_gatt_char(ENV_CONFIG_UUID)
        print(f"Raw bytes ({len(data)}): {data.hex()}")
        print(f"Bytes: {list(data)}")

asyncio.run(main())