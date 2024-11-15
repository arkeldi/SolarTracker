import time
import board
import smbus2
import bme280
import busio
import digitalio
import adafruit_mcp3xxx.mcp3008 as MCP
from adafruit_mcp3xxx.analog_in import AnalogIn
from picamera2 import Picamera2
import requests
from datetime import datetime
import os
import json
import subprocess
import threading

# BME280 sensor address (default address)
address = 0x76

# Initialize I2C bus
try:
    bus = smbus2.SMBus(1)
    # Load calibration parameters
    calibration_params = bme280.load_calibration_params(bus, address)
    sensor_initialized = True
except Exception as e:
    print(f"Failed to initialize BME280 sensor: {e}")
    sensor_initialized = False

# Initialize MCP3008
try:
    spi = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)
    cs = digitalio.DigitalInOut(board.D5)
    mcp = MCP.MCP3008(spi, cs)
    channel = AnalogIn(mcp, MCP.P0)
    mcp_initialized = True
except Exception as e:
    print(f"Failed to initialize MCP3008: {e}")
    mcp_initialized = False

# Initialize Picamera2
try:
    picam2 = Picamera2()
    picam2.configure(picam2.create_still_configuration(main={"size": (1440, 1080)}))
    picam2.start(show_preview=False)
except Exception as e:
    print(f"Error initializing Picamera2: {e}")

# Create directories if they don't exist
IMAGE_DIR = "images"
DATA_FILE = "data/data.json"
if not os.path.exists(IMAGE_DIR):
    os.makedirs(IMAGE_DIR)
if not os.path.exists(os.path.dirname(DATA_FILE)):
    os.makedirs(os.path.dirname(DATA_FILE))

# Global variable to store weather station data
ambient_weather_data = {}

def read_sensor_data(retries=5, delay=2):
    for _ in range(retries):
        try:
            data = bme280.sample(bus, address, calibration_params)
            temperature_c = data.temperature
            temperature_f = (temperature_c * 9/5) + 32
            pressure_hpa = data.pressure
            humidity = data.humidity
            return temperature_c, temperature_f, humidity, pressure_hpa 
        except Exception as e:
            print(f"Error reading BME280 sensor data: {e}")
            time.sleep(delay)
    return None, None, None, None

def take_image():
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(IMAGE_DIR, f"image_{current_time}.jpg")
    try:
        picam2.capture_file(filename)
    except Exception as e:
        print(f"Error capturing image: {e}")
        return None
    return filename

def save_data_locally(data):
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            all_data = json.load(f)
    else:
        all_data = []

    all_data.append(data)

    with open(DATA_FILE, 'w') as f:
        json.dump(all_data, f, indent=4)

def send_data(data, image_path, retries=3):
    """Combined function to send both data and image in a single request"""
    if image_path is None:
        print("No image to send.")
        return

    for _ in range(retries):
        try:
            # Prepare the multipart form data
            files = {
                'image': ('image.jpg', open(image_path, 'rb'), 'image/jpeg')
            }
            
            # Prepare the data payload matching the new backend structure
            data_payload = {
                'temperature_c': data.get('temperature_c', 0),
                'temperature_f': data.get('temperature_f', 0),
                'humidity': data.get('humidity', 0),
                'air_pressure': 0,  # Add if you have this data
                'wind_speed': data.get('ambientWeatherWindSpeed', 0),
                'wind_direction': data.get('ambientWeatherWindDirection', 0),
                'timestamp': data.get('timestamp'),
                'pressure': data.get('pressure', 0),
                'ambientWeatherBatteryOk': data.get('ambientWeatherBatteryOk', False),
                'ambientWeatherTemp': data.get('ambientWeatherTemp', 0),
                'ambientWeatherHumidity': data.get('ambientWeatherHumidity', 0),
                'ambientWeatherWindDirection': data.get('ambientWeatherWindDirection', 0),
                'ambientWeatherWindSpeed': data.get('ambientWeatherWindSpeed', 0),
                'ambientWeatherWindMaxSpeed': data.get('ambientWeatherWindMaxSpeed', 0),
                'ambientWeatherRain': data.get('ambientWeatherRain', 0),
                'ambientWeatherUV': data.get('ambientWeatherUV', 0),
                'ambientWeatherUVI': data.get('ambientWeatherUVI', 0),
                'ambientWeatherLightLux': data.get('ambientWeatherLightLux', 0)
            }

            # Send POST request with both data and image
            response = requests.post(
                'http://sunsightenergy.com/api/insert-data',
                files=files,
                data=data_payload
            )
            print(f"Server response: {response.text}")
            return
        except requests.exceptions.RequestException as e:
            print(f"Error sending data and image: {e}")
            time.sleep(5)

def fetch_weather_station_data():
    global ambient_weather_data
    try:
        process = subprocess.Popen(
            ["rtl_433", "-M", "utc", "-F", "json", "-R", "78", "-f", "914980000", "-s", "250000"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        while True:
            output = process.stdout.readline()
            if output:
                last_line = output.strip()
                try:
                    weather_data = json.loads(last_line)
                    ambient_weather_data = {
                         "ambientWeatherTimestamp": weather_data.get('time'),
                         "ambientWeatherModel": weather_data.get('model'),
                         "ambientWeatherId": weather_data.get('id'),
                         "ambientWeatherBatteryOk": weather_data.get('battery_ok'),
                         "ambientWeatherTemp": weather_data.get('temperature_C'),
                         "ambientWeatherHumidity": weather_data.get('humidity'),
                         "ambientWeatherWindDirection": weather_data.get('wind_dir_deg'),
                         "ambientWeatherWindSpeed": weather_data.get('wind_avg_m_s'),
                         "ambientWeatherWindMaxSpeed": weather_data.get('wind_max_m_s'),
                         "ambientWeatherRain": weather_data.get('rain_mm'),
                         "ambientWeatherUV": weather_data.get('uv'),
                         "ambientWeatherUVI": weather_data.get('uvi'),
                         "ambientWeatherLightLux": weather_data.get('light_lux'),
                         "ambientWeatherMIC": weather_data.get('mic')
                        }
                    print(f"Weather Station Data: {ambient_weather_data}")
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON: {e}")
            time.sleep(30)
    except Exception as e:
        print(f"Error fetching weather station data: {e}")

# Modify the main loop
if __name__ == "__main__":
    last_send_time = time.time()

    # Start fetching weather station data in a separate thread
    weather_thread = threading.Thread(target=fetch_weather_station_data)
    weather_thread.daemon = True
    weather_thread.start()

    while True:
        if sensor_initialized:
            try:
                temperature_c, temperature_f, humidity, pressure_hpa = read_sensor_data()
                if temperature_c is not None:
                    current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print(f"Time={current_time_str}, Temp={temperature_c:0.1f} C, Temp={temperature_f:0.1f} F, Humidity={humidity:0.1f}%, Pressure={pressure_hpa:0.2f}hPa")
            except Exception as e:
                print(f"Error in reading sensor data: {e}")
                temperature_c = temperature_f = humidity = pressure_hpa = 0
        else:
            temperature_c = temperature_f = humidity = pressure_hpa = 0

        current_time = time.time()

        # Send data and image every 1 minute
        if current_time - last_send_time >= 60:
            try:
                # Take new image
                image_path = take_image()
                
                # Prepare data payload
                data = {
                    "temperature_c": temperature_c,
                    "temperature_f": temperature_f,
                    "humidity": humidity,
                    "pressure": pressure_hpa,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    **ambient_weather_data
                }

                # Send both data and image in a single request
                send_data(data, image_path)
                last_send_time = current_time
            except Exception as e:
                print(f"Error in sending data and image: {e}")
            
        time.sleep(5)