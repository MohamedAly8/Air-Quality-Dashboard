import asyncio
import sqlite3
import struct
from datetime import datetime, timezone
from bleak import BleakClient, BleakScanner

# --- CONFIGURATION ---
THINGY_ADDRESS = "D7BD6C56-3226-E270-5080-C60DFB8E5A28" 
SCAN_MODE = False

# UUIDs
TEMP_UUID     = "ef680201-9b35-4933-9b10-52ffa9740042"
PRESSURE_UUID = "ef680202-9b35-4933-9b10-52ffa9740042"
HUMIDITY_UUID = "ef680203-9b35-4933-9b10-52ffa9740042"
AIR_UUID      = "ef680204-9b35-4933-9b10-52ffa9740042"
COLOR_UUID    = "ef680205-9b35-4933-9b10-52ffa9740042"
ENV_CONFIG_UUID = "ef680206-9b35-4933-9b10-52ffa9740042"
BATTERY_UUID  = "00002a19-0000-1000-8000-00805f9b34fb"

DB_PATH = "thingy.db"
db_queue = asyncio.Queue()

# We include sound_db: None so the database column count matches (11 total)
latest = {
    "temperature": None, "humidity": None, "pressure": None, 
    "co2": None, "tvoc": None, "lux": None, 
    "red": None, "green": None, "blue": None, "sound_db": None
}

# --- DATABASE ---
def init_db():
    con = sqlite3.connect(DB_PATH)
    # This creates the table with all 11 columns to match your existing file
    con.execute("""CREATE TABLE IF NOT EXISTS readings (
        ts TEXT, temperature REAL, humidity REAL, pressure REAL, 
        co2 INTEGER, tvoc INTEGER, lux REAL, red INTEGER, 
        green INTEGER, blue INTEGER, sound_db REAL)""")
    con.commit()
    return con

# --- PARSERS ---
def parse_temp(data):
    i, d = struct.unpack_from("<bB", data)
    return i + d / 100

def parse_pressure(data):
    i, d = struct.unpack_from("<IB", data)
    return i + d / 100

def parse_color(data):
    r, g, b, clear = struct.unpack_from("<HHHH", data)
    return r, g, b, round(clear * 0.0609, 1)

async def db_worker(con):
    while True:
        data = await db_queue.get()
        try:
            # We use 11 placeholders now to match the table
            con.execute("INSERT INTO readings VALUES (?,?,?,?,?,?,?,?,?,?,?)", data)
            con.commit()
        except Exception as e:
            print(f"DB Error: {e}")
        db_queue.task_done()

# --- MAIN ---
async def main():
    if SCAN_MODE:
        print("Scanning...")
        devices = await BleakScanner.discover()
        for d in devices:
            if d.name and "Thingy" in d.name:
                print(f"FOUND: {d.address}")
        return

    con = init_db()
    asyncio.create_task(db_worker(con))

    async with BleakClient(THINGY_ADDRESS) as client:
        print(f"Connected to {THINGY_ADDRESS}!")

        # 1s Intervals
        fast_cfg = bytearray([0xE8, 0x03, 0xE8, 0x03, 0xE8, 0x03, 0xE8, 0x03, 0xE8, 0x03])
        await client.write_gatt_char(ENV_CONFIG_UUID, fast_cfg, response=False)

        def on_temp(_, d): latest["temperature"] = parse_temp(d)
        def on_hum(_, d):  latest["humidity"] = struct.unpack("<B", d)[0]
        def on_pres(_, d): latest["pressure"] = parse_pressure(d)
        def on_air(_, d):  latest["co2"], latest["tvoc"] = struct.unpack("<HH", d)
        def on_col(_, d):  latest["red"], latest["green"], latest["blue"], latest["lux"] = parse_color(d)

        uuids = [(TEMP_UUID, on_temp), (PRESSURE_UUID, on_pres), 
                 (HUMIDITY_UUID, on_hum), (AIR_UUID, on_air), (COLOR_UUID, on_col)]
        
        for uuid, cb in uuids:
            await client.start_notify(uuid, cb)

        print("Streaming 1s data. Press Ctrl+C to stop.\n")
        
        while client.is_connected:
            # Only save/print once we have basic data to avoid NoneType errors
            if latest["temperature"] is not None and latest["lux"] is not None:
                # 1. Save to DB
                snapshot = (datetime.now(timezone.utc).isoformat(), *latest.values())
                db_queue.put_nowait(snapshot)
                
                # 2. Safe Print
                co2 = f"{latest['co2']}ppm" if latest['co2'] else "warming..."
                lux = f"{latest['lux']:.0f}"
                print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                      f"Temp: {latest['temperature']:.1f}°C | Lux: {lux} | CO2: {co2}")
            
            await asyncio.sleep(1.0)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopping...")