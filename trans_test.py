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
bus = smbus2.SMBus(1)

# Load calibration parameters
calibration_params = bme280.load_calibration_params(bus, address)


# Initialize MCP3008
spi = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)
cs = digitalio.DigitalInOut(board.D5)
mcp = MCP.MCP3008(spi, cs)
channel = AnalogIn(mcp, MCP.P0)

# Initialize Picamera2
picam2 = Picamera2()
picam2.start(show_preview=False)

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
            print(f"Error reading sensor data: {e}")
            time.sleep(delay)
            return None, None, None, None

def take_image():
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(IMAGE_DIR, f"image_{current_time}.jpg")
    picam2.capture_file(filename)
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

def send_data(data, retries=3):
    save_data_locally(data)
    for _ in range(retries):
        try:
            response = requests.post('http://18.226.186.142/data', json=data)
            print(response.text)
            return
        except requests.exceptions.RequestException as e:
            print(f"Error sending data: {e}")
            time.sleep(5)

def send_image(image_path, retries=3):
    for _ in range(retries):
        try:
            image_file = {'file': open(image_path, 'rb')}
            response = requests.post('http://18.226.186.142/upload_image', files=image_file)
            print(response.text)
            return
        except requests.exceptions.RequestException as e:
            print(f"Error sending image: {e}")
            time.sleep(5)

def fetch_weather_station_data():
    global ambient_weather_data
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
                    "ambientWeatherTemp": weather_data.get('temperature_C'),
                    "ambientWeatherHumidity": weather_data.get('humidity'),
                    "ambientWeatherSolarRadiation": weather_data.get('light_lux') * 0.0079,
                    "ambientWeatherWindSpeed": weather_data.get('wind_avg_m_s'),
                    "ambientWeatherWindDirection": weather_data.get('wind_dir_deg'),
                    "ambientWeatherTimestamp": weather_data.get('time')
                }
                print(f"Weather Station Data: {ambient_weather_data}")
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON: {e}")
        # else:
        #     ambient_weather_data = {
        #         "ambientWeatherTemp": weather_data.get('temperature_C'),
        #         "ambientWeatherHumidity": weather_data.get('humidity'),
        #         "ambientWeatherSolarRadiation": weather_data.get('light_lux') * 0.0079,
        #         "ambientWeatherWindSpeed": weather_data.get('wind_avg_m_s'),
        #         "ambientWeatherWindDirection": weather_data.get('wind_dir_deg'),
        #         "ambientWeatherTimestamp": weather_data.get('time')
        #     }
        time.sleep(30)

if __name__ == "__main__":
    last_data_send_time = time.time()
    last_image_send_time = time.time()

    # Start fetching weather station data in a separate thread
    weather_thread = threading.Thread(target=fetch_weather_station_data)
    weather_thread.daemon = True
    weather_thread.start()

    while True:
        temperature_c, temperature_f, humidity, pressure_hpa = read_sensor_data()
        if temperature_c is not None:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"Time={current_time}, Temp={temperature_c:0.1f} C, Temp={temperature_f:0.1f} F, Humidity={humidity:0.1f}%, Pressure={pressure_hpa:0.2f}hPa")
        
        current_time = time.time()

        # Send data every 5 minutes
        if current_time - last_data_send_time >= (1 * 60):
            # Combine sensor data and ambient weather data
            data = {
                "temperature_c": temperature_c,
                "temperature_f": temperature_f,
                "humidity": humidity,
                "pressure": pressure_hpa,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                **ambient_weather_data
            }

            send_data(data)
            last_data_send_time = current_time

        # Send image every 30 minutes
        if current_time - last_image_send_time >= (30 * 60):
            image_path = take_image()
            send_image(image_path)
            last_image_send_time = current_time
        
        time.sleep(5)