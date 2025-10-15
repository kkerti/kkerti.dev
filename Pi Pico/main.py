import machine
from machine import Pin
import onewire
import ds18x20
import time
import network
import urequests
import json

# WiFi Configuration
WIFI_SSID = "Manul"
WIFI_PASSWORD = "***"

# API Configuration
# Use your MacBook's local IP address from SvelteKit dev server
# Run: npm run dev -- --host to get the network address
API_ENDPOINT = "http://192.168.0.193:5173/lab/api"  # Replace with your Mac's IP and port
API_KEY = ""  # Probably not needed for local development

# Set up LED
led = Pin("LED", Pin.OUT)

# Set up DS18B20 temperature sensor on GPIO 22
dat = Pin(22)
ds = ds18x20.DS18X20(onewire.OneWire(dat))

# Scan for DS18B20 devices
roms = ds.scan()
print('Found DS18B20 devices:', roms)

if len(roms) == 0:
    print("No DS18B20 sensor found! Check wiring.")

# WiFi connection function
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    if not wlan.isconnected():
        print('Connecting to WiFi...')
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        
        # Wait for connection with timeout
        max_wait = 10
        while max_wait > 0:
            if wlan.status() < 0 or wlan.status() >= 3:
                break
            max_wait -= 1
            print('Waiting for connection...')
            time.sleep(1)
    
    if wlan.isconnected():
        print('WiFi connected!')
        print('IP:', wlan.ifconfig()[0])
        return True
    else:
        print('WiFi connection failed')
        return False

# Function to send temperature data to API
def send_to_api(temp_celsius):
    try:
        # Prepare data payload
        temp_fahrenheit = temp * 9/5 + 32
        data = {
            "temperature": round(temp_celsius, 2),
            "timestamp": time.time(),
            "device_id": "pico_w_001"  # Optional: identifier for your device
        }
        
        # Prepare headers
        headers = {
            "Content-Type": "application/json"
        }
        
        # Add API key to headers if you're using authentication
        if API_KEY:
            headers["Authorization"] = f"Bearer {API_KEY}"
            # Or use: headers["X-API-Key"] = API_KEY
        
        # Make POST request
        response = urequests.post(
            API_ENDPOINT,
            json=data,
            headers=headers
        )
        
        print(f'API Response: {response.status_code}')
        print(f'Response body: {response.text}')
        response.close()
        
        return response.status_code == 200
        
    except Exception as e:
        print(f'Error sending to API: {e}')
        return False

# Connect to WiFi at startup
wifi_connected = connect_wifi()

# Main loop
print("Starting temperature monitoring with API upload...")
while True:
    # Blink LED
    led.on()
    
    # Read temperature
    ds.convert_temp()
    time.sleep_ms(750)  # Wait for conversion
    
    for rom in roms:
        temp = ds.read_temp(rom)
        print(f'Temperature: {temp:.1f}°C ({temp * 9/5 + 32:.1f}°F)')
        
        # Send to API if WiFi is connected
        if wifi_connected:
            success = send_to_api(temp)
            if success:
                print("Data sent successfully!")
            else:
                print("Failed to send data")
                # Try reconnecting WiFi if send failed
                wifi_connected = connect_wifi()
    
    # Turn off LED
    led.off()
    
    # Wait before next reading
    time.sleep(2)  # Increased to 10 seconds to avoid overwhelming the API