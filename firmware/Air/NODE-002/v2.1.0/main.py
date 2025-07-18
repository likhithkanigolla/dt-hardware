import time
import json
import machine
import network
import urequests

# main.py - Firmware for Air NODE-002
# Digital Twin Project v2


# Configuration
DEVICE_ID = "NODE-002"
DEVICE_TYPE = "Air"
VERSION = "1.0.0"
API_ENDPOINT = "https://your-digital-twin-server.com/api/data"
WIFI_SSID = "your_wifi_ssid"
WIFI_PASSWORD = "your_wifi_password"
SAMPLE_INTERVAL = 60  # seconds

# Initialize sensors
i2c = machine.I2C(scl=machine.Pin(22), sda=machine.Pin(21))
# Add your specific sensor initialization here

# Status LED
status_led = machine.Pin(2, machine.Pin.OUT)

def connect_wifi():
    """Connect to WiFi network"""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    if not wlan.isconnected():
        print("Connecting to WiFi...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        
        max_wait = 10
        while max_wait > 0:
            if wlan.isconnected():
                break
            max_wait -= 1
            status_led.value(not status_led.value())
            time.sleep(1)
            
    if wlan.isconnected():
        print("Connected to WiFi")
        print("IP:", wlan.ifconfig()[0])
        status_led.value(1)
        return True
    else:
        print("Failed to connect to WiFi")
        status_led.value(0)
        return False

def read_sensors():
    """Read data from sensors"""
    # Replace with actual sensor reading code
    return {
        "temperature": 25.0,
        "humidity": 50.0,
        "pressure": 1013.25,
        "air_quality": 100.0
    }

def send_data(data):
    """Send data to digital twin server"""
    payload = {
        "device_id": DEVICE_ID,
        "device_type": DEVICE_TYPE,
        "version": VERSION,
        "timestamp": time.time(),
        "data": data
    }
    
    try:
        response = urequests.post(
            API_ENDPOINT,
            headers={'Content-Type': 'application/json'},
            data=json.dumps(payload)
        )
        print("Data sent. Response:", response.text)
        response.close()
        return True
    except Exception as e:
        print("Error sending data:", e)
        return False

def main():
    """Main function"""
    if not connect_wifi():
        pass
    
    while True:
        if not network.WLAN(network.STA_IF).isconnected():
            connect_wifi()
        
        status_led.value(not status_led.value())
        
        sensor_data = read_sensors()
        print("Sensor data:", sensor_data)
        
        if sensor_data:
            send_data(sensor_data)
        
        status_led.value(0)
        time.sleep(SAMPLE_INTERVAL)

# Start the application
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        with open("error_log.txt", "a") as f:
            f.write(f"{time.time()}: {str(e)}\n")
        machine.reset()