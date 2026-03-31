#!/usr/bin/env python3
"""
Comprehensive Raspberry Pi 3B+ Hardware Control and Sensor Integration
Combines GPIO control (LED, buzzer, motor, fan, light, relay, buttons, PIR)
with sensor integration (VEML7700, SI7021, SGP30, ultrasonic, SDS011)
and WLED strip management with button control
"""

import time
import json
import serial
import threading
from datetime import datetime

# Check for required modules
try:
    import board
    import adafruit_veml7700
    import adafruit_si7021
    import adafruit_sgp30
    import RPi.GPIO as GPIO
    import neopixel
except ImportError as e:
    print("\n" + "=" * 60)
    print("ERROR: Missing required dependencies!")
    print("=" * 60)
    print(f"\nError details: {e}\n")
    print("Please install the required packages:")
    print("\nFor Raspberry Pi, run these commands:")
    print("  pip3 install RPi.GPIO")
    print("  pip3 install adafruit-blinka")
    print("  pip3 install adafruit-circuitpython-veml7700")
    print("  pip3 install adafruit-circuitpython-si7021")
    print("  pip3 install adafruit-circuitpython-sgp30")
    print("  pip3 install rpi_ws281x adafruit-circuitpython-neopixel")
    print("\nOr install all at once:")
    print("  pip3 install RPi.GPIO adafruit-blinka adafruit-circuitpython-veml7700 adafruit-circuitpython-si7021 adafruit-circuitpython-sgp30 rpi_ws281x adafruit-circuitpython-neopixel")
    print("\nIf using a virtual environment, make sure it's activated first!")
    print("=" * 60 + "\n")
    exit(1)


# ============================================================================
# GPIO PIN CONFIGURATION
# ============================================================================
class GPIOConfig:
    """Centralized GPIO pin configuration"""
    # Simple outputs
    LED = 4
    BUZZER = 22
    MOTOR = 18
    FAN = 23
    LIGHT = 24
    
    # Ultrasonic sensor
    ULTRASONIC_TRIG = 23  # Note: Shared with FAN, needs manual configuration
    ULTRASONIC_ECHO = 24  # Note: Shared with LIGHT, needs manual configuration
    
    # Button inputs
    BUTTONS = [19, 5, 6, 12, 13, 16, 20, 21]
    
    # PIR motion sensor
    PIR_PIN = 17
    
    # Serial port for dust sensor (SDS011)
    DUST_SENSOR_PORT = '/dev/ttyAMA1'
    DUST_SENSOR_BAUDRATE = 9600
    
    # LED strip
    LED_STRIP_PIN = board.D18
    LED_STRIP_COUNT = 30
    LED_STRIP_BRIGHTNESS = 0.3


# ============================================================================
# SENSOR CLASSES
# ============================================================================

class VEML7700:
    """Class to interface with VEML7700 ambient light sensor"""
    
    def __init__(self):
        """Initialize the VEML7700 sensor"""
        try:
            i2c = board.I2C()
            self.sensor = adafruit_veml7700.VEML7700(i2c)
            print("✓ VEML7700 sensor initialized successfully")
        except Exception as e:
            print(f"✗ Error initializing VEML7700 sensor: {e}")
            raise
    
    def read_lux(self):
        """Read ambient light in lux"""
        try:
            return round(self.sensor.lux, 2)
        except Exception as e:
            print(f"Error reading lux: {e}")
            return None
    
    def read_white_light(self):
        """Read white light level"""
        try:
            return round(self.sensor.white, 2)
        except Exception as e:
            print(f"Error reading white light: {e}")
            return None
    
    def read_light(self):
        """Read raw light level"""
        try:
            return round(self.sensor.light, 2)
        except Exception as e:
            print(f"Error reading light: {e}")
            return None
    
    def get_all_readings(self):
        """Get all sensor readings at once"""
        return {
            'lux': self.read_lux(),
            'white_light': self.read_white_light(),
            'light': self.read_light(),
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }


class SI7021:
    """Class to interface with SI7021 temperature and humidity sensor"""
    
    def __init__(self):
        """Initialize the SI7021 sensor"""
        try:
            i2c = board.I2C()
            self.sensor = adafruit_si7021.SI7021(i2c)
            print("✓ SI7021 sensor initialized successfully")
        except Exception as e:
            print(f"✗ Error initializing SI7021 sensor: {e}")
            raise
    
    def read_temperature(self):
        """Read temperature in Celsius"""
        try:
            return round(self.sensor.temperature, 2)
        except Exception as e:
            print(f"Error reading temperature: {e}")
            return None
    
    def read_humidity(self):
        """Read relative humidity"""
        try:
            return round(self.sensor.relative_humidity, 2)
        except Exception as e:
            print(f"Error reading humidity: {e}")
            return None
    
    def read_temperature_fahrenheit(self):
        """Read temperature in Fahrenheit"""
        temp_c = self.read_temperature()
        if temp_c is not None:
            return round((temp_c * 9/5) + 32, 2)
        return None
    
    def get_all_readings(self):
        """Get all sensor readings at once"""
        return {
            'temperature_c': self.read_temperature(),
            'temperature_f': self.read_temperature_fahrenheit(),
            'humidity': self.read_humidity(),
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }


class SGP30:
    """Class to interface with SGP30 VOC and eCO2 gas sensor"""
    
    def __init__(self):
        """Initialize the SGP30 sensor"""
        try:
            i2c = board.I2C()
            self.sensor = adafruit_sgp30.Adafruit_SGP30(i2c)
            print("✓ SGP30 sensor initialized...")
            print("  Initializing SGP30 baseline (this takes ~15 seconds)...")
            self.sensor.iaq_init()
            self.sensor.set_iaq_baseline(0x8973, 0x8AAE)
            print("✓ SGP30 ready for air quality measurements")
        except Exception as e:
            print(f"✗ Error initializing SGP30 sensor: {e}")
            raise
    
    def read_eco2(self):
        """Read eCO2 (equivalent CO2) in ppm"""
        try:
            return self.sensor.eCO2
        except Exception as e:
            print(f"Error reading eCO2: {e}")
            return None
    
    def read_tvoc(self):
        """Read TVOC (Total Volatile Organic Compounds) in ppb"""
        try:
            return self.sensor.TVOC
        except Exception as e:
            print(f"Error reading TVOC: {e}")
            return None
    
    def get_baseline(self):
        """Get baseline calibration values for long-term storage"""
        try:
            eco2_base, tvoc_base = self.sensor.iaq_get_baseline()
            return {'eco2_baseline': eco2_base, 'tvoc_baseline': tvoc_base}
        except Exception as e:
            print(f"Error getting baseline: {e}")
            return None
    
    def get_all_readings(self):
        """Get all sensor readings at once"""
        return {
            'eco2': self.read_eco2(),
            'tvoc': self.read_tvoc(),
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }


class UltrasonicSensor:
    """Class to interface with RCWL-1601 ultrasonic distance sensor"""
    
    def __init__(self, trig_pin=23, echo_pin=24):
        """
        Initialize the ultrasonic sensor
        Args:
            trig_pin: GPIO pin number for TRIG
            echo_pin: GPIO pin number for ECHO
        """
        try:
            self.trig_pin = trig_pin
            self.echo_pin = echo_pin
            
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            
            GPIO.setup(self.trig_pin, GPIO.OUT)
            GPIO.setup(self.echo_pin, GPIO.IN)
            
            GPIO.output(self.trig_pin, False)
            time.sleep(0.1)
            
            print(f"✓ RCWL-1601 Ultrasonic sensor initialized (TRIG: GPIO{trig_pin}, ECHO: GPIO{echo_pin})")
        except Exception as e:
            print(f"✗ Error initializing ultrasonic sensor: {e}")
            raise
    
    def read_distance(self, unit='cm'):
        """
        Measure distance using ultrasonic sensor
        Args:
            unit: 'cm' for centimeters, 'inch' for inches, 'm' for meters
        Returns:
            Distance in specified unit, or None if error
        """
        try:
            GPIO.output(self.trig_pin, True)
            time.sleep(0.00001)
            GPIO.output(self.trig_pin, False)
            
            timeout = time.time() + 0.1
            while GPIO.input(self.echo_pin) == 0:
                pulse_start = time.time()
                if pulse_start > timeout:
                    return None
            
            timeout = time.time() + 0.1
            while GPIO.input(self.echo_pin) == 1:
                pulse_end = time.time()
                if pulse_end > timeout:
                    return None
            
            pulse_duration = pulse_end - pulse_start
            distance_cm = (pulse_duration * 34300) / 2
            
            if unit == 'cm':
                return round(distance_cm, 2)
            elif unit == 'inch':
                return round(distance_cm / 2.54, 2)
            elif unit == 'm':
                return round(distance_cm / 100, 3)
            else:
                return round(distance_cm, 2)
                
        except Exception as e:
            print(f"Error reading distance: {e}")
            return None
    
    def get_all_readings(self):
        """Get all sensor readings at once"""
        distance_cm = self.read_distance('cm')
        distance_inch = self.read_distance('inch')
        
        return {
            'distance_cm': distance_cm,
            'distance_inch': distance_inch,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def cleanup(self):
        """Clean up GPIO pins"""
        try:
            GPIO.cleanup([self.trig_pin, self.echo_pin])
        except Exception as e:
            print(f"Error cleaning up GPIO: {e}")


class DustSensor:
    """Class to interface with SDS011 dust/particle sensor via serial"""
    
    def __init__(self, port=GPIOConfig.DUST_SENSOR_PORT, baudrate=GPIOConfig.DUST_SENSOR_BAUDRATE):
        """
        Initialize the dust sensor
        Args:
            port: Serial port (default: /dev/ttyAMA1)
            baudrate: Baud rate (default: 9600)
        """
        try:
            self.ser = serial.Serial(port, baudrate, timeout=2)
            print(f"✓ SDS011 Dust Sensor initialized on {port}")
        except Exception as e:
            print(f"✗ Error initializing SDS011 sensor: {e}")
            self.ser = None
    
    def read_pm_values(self):
        """Read PM2.5 and PM10 values"""
        if not self.ser:
            return None
        
        try:
            data = self.ser.read(10)
            
            if len(data) == 10:
                if data[0] == 0xAA and data[1] == 0xC0:
                    pm25 = (data[2] + data[3]*256) / 10
                    pm10 = (data[4] + data[5]*256) / 10
                    
                    return {
                        'pm25': round(pm25, 2),
                        'pm10': round(pm10, 2),
                        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                    }
            return None
        except Exception as e:
            print(f"Error reading dust sensor: {e}")
            return None
    
    def cleanup(self):
        """Close serial connection"""
        try:
            if self.ser:
                self.ser.close()
        except Exception as e:
            print(f"Error closing serial connection: {e}")


# ============================================================================
# DEVICE CONTROL CLASSES
# ============================================================================

class LEDController:
    """Class to control LED"""
    
    def __init__(self, pin=GPIOConfig.LED):
        self.pin = pin
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.pin, GPIO.OUT)
        GPIO.output(self.pin, GPIO.LOW)
        print(f"✓ LED initialized on GPIO{pin}")
    
    def turn_on(self):
        """Turn LED on"""
        GPIO.output(self.pin, GPIO.HIGH)
        print("💡 LED ON")
    
    def turn_off(self):
        """Turn LED off"""
        GPIO.output(self.pin, GPIO.LOW)
        print("💡 LED OFF")
    
    def toggle(self):
        """Toggle LED state"""
        current = GPIO.input(self.pin)
        GPIO.output(self.pin, not current)
        print(f"💡 LED toggled to {'ON' if not current else 'OFF'}")


class BuzzerController:
    """Class to control buzzer"""
    
    def __init__(self, pin=GPIOConfig.BUZZER):
        self.pin = pin
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.pin, GPIO.OUT)
        GPIO.output(self.pin, GPIO.LOW)
        print(f"✓ Buzzer initialized on GPIO{pin}")
    
    def beep(self, duration=0.5):
        """Beep buzzer"""
        GPIO.output(self.pin, GPIO.HIGH)
        time.sleep(duration)
        GPIO.output(self.pin, GPIO.LOW)
        print(f"🔔 Buzzer beeped ({duration}s)")
    
    def turn_on(self):
        """Turn buzzer on"""
        GPIO.output(self.pin, GPIO.HIGH)
        print("🔔 Buzzer ON")
    
    def turn_off(self):
        """Turn buzzer off"""
        GPIO.output(self.pin, GPIO.LOW)
        print("🔔 Buzzer OFF")


class MotorController:
    """Class to control motor with PWM"""
    
    def __init__(self, pin=GPIOConfig.MOTOR, frequency=1000):
        self.pin = pin
        self.frequency = frequency
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.pin, GPIO.OUT)
        self.pwm = GPIO.PWM(self.pin, frequency)
        self.pwm.start(0)
        print(f"✓ Motor initialized on GPIO{pin} at {frequency}Hz")
    
    def set_speed(self, duty_cycle):
        """
        Set motor speed via duty cycle
        Args:
            duty_cycle: 0-100 (percentage)
        """
        self.pwm.ChangeDutyCycle(duty_cycle)
        print(f"⚙️  Motor speed set to {duty_cycle}%")
    
    def turn_on(self, speed=70):
        """Turn motor on at specified speed"""
        self.set_speed(speed)
    
    def turn_off(self):
        """Turn motor off"""
        self.set_speed(0)
        print("⚙️  Motor OFF")
    
    def cleanup(self):
        """Clean up PWM"""
        self.pwm.stop()


class FanController:
    """Class to control fan"""
    
    def __init__(self, pin=GPIOConfig.FAN):
        self.pin = pin
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.pin, GPIO.OUT, initial=GPIO.HIGH)
        print(f"✓ Fan initialized on GPIO{pin}")
    
    def turn_on(self):
        """Turn fan on"""
        GPIO.output(self.pin, GPIO.LOW)
        print("💨 Fan ON")
    
    def turn_off(self):
        """Turn fan off"""
        GPIO.output(self.pin, GPIO.HIGH)
        print("💨 Fan OFF")


class LightController:
    """Class to control light"""
    
    def __init__(self, pin=GPIOConfig.LIGHT):
        self.pin = pin
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.pin, GPIO.OUT, initial=GPIO.HIGH)
        print(f"✓ Light initialized on GPIO{pin}")
    
    def turn_on(self):
        """Turn light on"""
        GPIO.output(self.pin, GPIO.LOW)
        print("💡 Light ON")
    
    def turn_off(self):
        """Turn light off"""
        GPIO.output(self.pin, GPIO.HIGH)
        print("💡 Light OFF")


class RelayController:
    """Class to control fan and light via relay"""
    
    def __init__(self):
        self.fan = FanController(GPIOConfig.FAN)
        self.light = LightController(GPIOConfig.LIGHT)
        print("✓ Relay controller initialized")
    
    def turn_all_on(self):
        """Turn fan and light on"""
        self.fan.turn_on()
        self.light.turn_on()
    
    def turn_all_off(self):
        """Turn fan and light off"""
        self.fan.turn_off()
        self.light.turn_off()


class PIRSensor:
    """Class to detect motion via PIR sensor"""
    
    def __init__(self, pin=GPIOConfig.PIR_PIN):
        self.pin = pin
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.pin, GPIO.IN)
        print(f"✓ PIR sensor initialized on GPIO{pin}")
    
    def is_motion_detected(self):
        """Check if motion is detected"""
        return GPIO.input(self.pin) == GPIO.HIGH
    
    def get_status(self):
        """Get motion status"""
        return "Motion Detected" if self.is_motion_detected() else "No Motion"


class ButtonController:
    """Class to handle button input"""
    
    def __init__(self, button_pin, label="Button"):
        self.button_pin = button_pin
        self.label = label
        self.pressed_count = 0
        self.last_button_state = False
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        print(f"✓ {label} initialized on GPIO{button_pin}")
    
    def check_press(self):
        """Check if button was pressed"""
        current_state = GPIO.input(self.button_pin) == GPIO.LOW
        
        if current_state and not self.last_button_state:
            self.last_button_state = current_state
            time.sleep(0.05)
            return True
        
        self.last_button_state = current_state
        return False
    
    def increment_count(self):
        """Increment press counter"""
        self.pressed_count += 1
        return self.pressed_count


class WLEDStripController:
    """Class to control WLED/NeoPixel LED strip"""
    
    def __init__(self, pixel_pin=GPIOConfig.LED_STRIP_PIN, 
                 num_pixels=GPIOConfig.LED_STRIP_COUNT, 
                 brightness=GPIOConfig.LED_STRIP_BRIGHTNESS):
        try:
            self.num_pixels = num_pixels
            self.pixels = neopixel.NeoPixel(
                pixel_pin, 
                num_pixels, 
                brightness=brightness, 
                auto_write=False,
                pixel_order=neopixel.GRB
            )
            self.pixels.fill((0, 0, 0))
            self.pixels.show()
            print(f"✓ WLED Strip initialized: {num_pixels} LEDs on GPIO18")
            
            self.sensor_colors = {
                'si7021': (0, 255, 0),
                'veml7700': (255, 255, 0),
                'sgp30': (0, 0, 255),
                'ultrasonic': (255, 0, 255),
                'pir': (255, 128, 0)
            }
            
            self.sensor_led_map = {
                'si7021': 0,
                'veml7700': 1,
                'sgp30': 2,
                'ultrasonic': 3,
                'pir': 4
            }
            
        except Exception as e:
            print(f"✗ Error initializing WLED strip: {e}")
            raise
    
    def set_sensor_led(self, sensor_name, state, animate=True):
        """Set LED for a specific sensor"""
        if sensor_name not in self.sensor_led_map:
            return
        
        led_index = self.sensor_led_map[sensor_name]
        color = self.sensor_colors.get(sensor_name, (255, 255, 255))
        
        if state:
            if animate:
                for brightness in range(0, 256, 25):
                    r = int(color[0] * brightness / 255)
                    g = int(color[1] * brightness / 255)
                    b = int(color[2] * brightness / 255)
                    self.pixels[led_index] = (r, g, b)
                    self.pixels.show()
                    time.sleep(0.05)
            else:
                self.pixels[led_index] = color
                self.pixels.show()
        else:
            if animate:
                current_color = self.pixels[led_index]
                for brightness in range(255, -1, -25):
                    r = int(current_color[0] * brightness / 255)
                    g = int(current_color[1] * brightness / 255)
                    b = int(current_color[2] * brightness / 255)
                    self.pixels[led_index] = (r, g, b)
                    self.pixels.show()
                    time.sleep(0.05)
            else:
                self.pixels[led_index] = (0, 0, 0)
                self.pixels.show()
    
    def turn_all_off(self):
        """Turn off all LEDs"""
        self.pixels.fill((0, 0, 0))
        self.pixels.show()
    
    def startup_animation(self):
        """Play startup animation"""
        print("🌈 Playing startup animation...")
        
        rainbow_colors = []
        for i in range(self.num_pixels):
            position = int((i / self.num_pixels) * 255)
            if position < 85:
                rainbow_colors.append((255 - position * 3, position * 3, 0))
            elif position < 170:
                position -= 85
                rainbow_colors.append((0, 255 - position * 3, position * 3))
            else:
                position -= 170
                rainbow_colors.append((position * 3, 0, 255 - position * 3))
        
        for i in range(self.num_pixels):
            self.pixels[i] = rainbow_colors[i]
            self.pixels.show()
            time.sleep(0.1)
        
        time.sleep(0.5)
        
        for _ in range(3):
            self.turn_all_off()
            time.sleep(0.2)
            for i in range(self.num_pixels):
                self.pixels[i] = rainbow_colors[i]
            self.pixels.show()
            time.sleep(0.2)
        
        for i in range(self.num_pixels):
            self.pixels[i] = rainbow_colors[i]
        self.pixels.show()
        
        print("✓ Animation complete! All LEDs ON.")


# ============================================================================
# MAIN SYSTEM INTEGRATION CLASS
# ============================================================================

class HardwareSystem:
    """Main class to manage all hardware components"""
    
    def __init__(self, enable_led=True, enable_sensors=True):
        """Initialize all hardware components"""
        print("\n" + "=" * 60)
        print("Initializing Comprehensive Hardware System")
        print("=" * 60 + "\n")
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Initialize sensors
        self.sensors = {}
        if enable_sensors:
            self.init_sensors()
        
        # Initialize device controllers
        self.init_devices()
        
        # Initialize LED strip
        if enable_led:
            try:
                self.led_strip = WLEDStripController()
                self.led_strip.startup_animation()
            except Exception as e:
                print(f"✗ Warning: Could not initialize LED strip: {e}")
                self.led_strip = None
        else:
            self.led_strip = None
        
        # Initialize button monitoring
        self.init_buttons()
        
        print("\n" + "=" * 60)
        print("✓ Hardware System initialized successfully!")
        print("=" * 60 + "\n")
    
    def init_sensors(self):
        """Initialize all sensors"""
        print("\n📊 Initializing Sensors:")
        print("-" * 60)
        
        try:
            self.sensors['veml7700'] = VEML7700()
        except Exception as e:
            print(f"✗ Skipping VEML7700: {e}")
            self.sensors['veml7700'] = None
        
        try:
            self.sensors['si7021'] = SI7021()
        except Exception as e:
            print(f"✗ Skipping SI7021: {e}")
            self.sensors['si7021'] = None
        
        try:
            self.sensors['sgp30'] = SGP30()
        except Exception as e:
            print(f"✗ Skipping SGP30: {e}")
            self.sensors['sgp30'] = None
        
        try:
            self.sensors['ultrasonic'] = UltrasonicSensor()
        except Exception as e:
            print(f"✗ Skipping Ultrasonic: {e}")
            self.sensors['ultrasonic'] = None
        
        try:
            self.sensors['dust'] = DustSensor()
        except Exception as e:
            print(f"✗ Skipping Dust Sensor: {e}")
            self.sensors['dust'] = None
        
        print()
    
    def init_devices(self):
        """Initialize all GPIO-controlled devices"""
        print("🔧 Initializing Devices:")
        print("-" * 60)
        
        try:
            self.led = LEDController()
        except Exception as e:
            print(f"✗ LED init failed: {e}")
            self.led = None
        
        try:
            self.buzzer = BuzzerController()
        except Exception as e:
            print(f"✗ Buzzer init failed: {e}")
            self.buzzer = None
        
        try:
            self.motor = MotorController()
        except Exception as e:
            print(f"✗ Motor init failed: {e}")
            self.motor = None
        
        try:
            self.fan = FanController()
        except Exception as e:
            print(f"✗ Fan init failed: {e}")
            self.fan = None
        
        try:
            self.light = LightController()
        except Exception as e:
            print(f"✗ Light init failed: {e}")
            self.light = None
        
        try:
            self.relay = RelayController()
        except Exception as e:
            print(f"✗ Relay init failed: {e}")
            self.relay = None
        
        try:
            self.pir = PIRSensor()
        except Exception as e:
            print(f"✗ PIR init failed: {e}")
            self.pir = None
        
        print()
    
    def init_buttons(self):
        """Initialize button monitoring"""
        print("🔘 Initializing Button Array:")
        print("-" * 60)
        
        self.buttons = {}
        for i, pin in enumerate(GPIOConfig.BUTTONS):
            try:
                self.buttons[pin] = ButtonController(pin, f"Button {i+1}")
            except Exception as e:
                print(f"✗ Button {i+1} init failed: {e}")
        
        if self.buttons:
            self.button_thread = threading.Thread(target=self._monitor_buttons, daemon=True)
            self.button_thread.start()
            print(f"\n✓ Button monitoring started ({len(self.buttons)} buttons)")
        else:
            print("\n✗ No buttons initialized")
        
        print()
    
    def _monitor_buttons(self):
        """Monitor buttons in background thread"""
        while True:
            try:
                for pin, button in self.buttons.items():
                    if button.check_press():
                        count = button.increment_count()
                        print(f"\n🔘 Button pressed on GPIO{pin} → Count: {count}")
                
                time.sleep(0.1)
            except Exception as e:
                print(f"Error in button monitoring: {e}")
                time.sleep(1)
    
    def read_all_sensors(self):
        """Read data from all available sensors"""
        data = {
            'timestamp': datetime.now().isoformat(),
            'sensors': {},
            'devices': self.get_device_status()
        }
        
        # Read all sensors
        if self.sensors.get('veml7700'):
            try:
                data['sensors']['veml7700'] = self.sensors['veml7700'].get_all_readings()
            except Exception as e:
                data['sensors']['veml7700'] = {'error': str(e)}
        
        if self.sensors.get('si7021'):
            try:
                data['sensors']['si7021'] = self.sensors['si7021'].get_all_readings()
            except Exception as e:
                data['sensors']['si7021'] = {'error': str(e)}
        
        if self.sensors.get('sgp30'):
            try:
                data['sensors']['sgp30'] = self.sensors['sgp30'].get_all_readings()
            except Exception as e:
                data['sensors']['sgp30'] = {'error': str(e)}
        
        if self.sensors.get('ultrasonic'):
            try:
                data['sensors']['ultrasonic'] = self.sensors['ultrasonic'].get_all_readings()
            except Exception as e:
                data['sensors']['ultrasonic'] = {'error': str(e)}
        
        if self.sensors.get('dust'):
            try:
                dust_data = self.sensors['dust'].read_pm_values()
                if dust_data:
                    data['sensors']['dust'] = dust_data
            except Exception as e:
                data['sensors']['dust'] = {'error': str(e)}
        
        if self.pir:
            try:
                data['sensors']['pir'] = {'motion': self.pir.is_motion_detected()}
            except Exception as e:
                data['sensors']['pir'] = {'error': str(e)}
        
        return data
    
    def get_device_status(self):
        """Get current status of all devices"""
        return {
            'led': 'initialized' if self.led else 'unavailable',
            'buzzer': 'initialized' if self.buzzer else 'unavailable',
            'motor': 'initialized' if self.motor else 'unavailable',
            'fan': 'initialized' if self.fan else 'unavailable',
            'light': 'initialized' if self.light else 'unavailable',
            'pir': 'initialized' if self.pir else 'unavailable',
            'led_strip': 'initialized' if self.led_strip else 'unavailable',
            'buttons': len(self.buttons)
        }
    
    def display_readings(self, data):
        """Display all sensor readings and system status"""
        print("\n" + "=" * 60)
        print(f"System Reading - {data['timestamp']}")
        print("=" * 60)
        
        # Device status
        print("\n🔧 DEVICE STATUS:")
        for device, status in data['devices'].items():
            print(f"  • {device.upper()}: {status}")
        
        # Sensor readings
        if data['sensors']:
            print("\n📊 SENSOR READINGS:")
            
            if 'veml7700' in data['sensors']:
                d = data['sensors']['veml7700']
                if 'error' not in d:
                    print(f"  📌 VEML7700 Light: {d.get('lux', 'N/A')} lux")
                else:
                    print(f"  📌 VEML7700: Error - {d['error']}")
            
            if 'si7021' in data['sensors']:
                d = data['sensors']['si7021']
                if 'error' not in d:
                    print(f"  🌡️  SI7021: {d.get('temperature_c', 'N/A')}°C ({d.get('humidity', 'N/A')}% RH)")
                else:
                    print(f"  🌡️  SI7021: Error - {d['error']}")
            
            if 'sgp30' in data['sensors']:
                d = data['sensors']['sgp30']
                if 'error' not in d:
                    print(f"  🌬️  SGP30: eCO2={d.get('eco2', 'N/A')} ppm, TVOC={d.get('tvoc', 'N/A')} ppb")
                else:
                    print(f"  🌬️  SGP30: Error - {d['error']}")
            
            if 'ultrasonic' in data['sensors']:
                d = data['sensors']['ultrasonic']
                if 'error' not in d:
                    print(f"  📏 Ultrasonic: {d.get('distance_cm', 'N/A')} cm")
                else:
                    print(f"  📏 Ultrasonic: Error - {d['error']}")
            
            if 'dust' in data['sensors']:
                d = data['sensors']['dust']
                if 'error' not in d:
                    print(f"  💨 Dust Sensor: PM2.5={d.get('pm25', 'N/A')} µg/m³, PM10={d.get('pm10', 'N/A')} µg/m³")
                else:
                    print(f"  💨 Dust Sensor: Error - {d['error']}")
            
            if 'pir' in data['sensors']:
                d = data['sensors']['pir']
                if 'error' not in d:
                    motion = "🔴 Motion Detected" if d.get('motion') else "🟢 No Motion"
                    print(f"  🚨 PIR: {motion}")
                else:
                    print(f"  🚨 PIR: Error - {d['error']}")
        
        print("\n" + "=" * 60)
    
    def log_to_file(self, data, filename='sensor_data.json'):
        """Log data to JSON file"""
        try:
            try:
                with open(filename, 'r') as f:
                    log_data = json.load(f)
            except FileNotFoundError:
                log_data = {'readings': []}
            
            log_data['readings'].append(data)
            
            with open(filename, 'w') as f:
                json.dump(log_data, f, indent=2)
            
            print(f"✓ Data logged to {filename}")
        except Exception as e:
            print(f"✗ Error logging to file: {e}")
    
    def demo_all_devices(self):
        """Run demonstration of all devices"""
        print("\n" + "=" * 60)
        print("DEVICE DEMONSTRATION")
        print("=" * 60)
        
        try:
            # LED demo
            if self.led:
                print("\n💡 LED Demonstration:")
                self.led.turn_on()
                time.sleep(1)
                self.led.turn_off()
                time.sleep(0.5)
            
            # Buzzer demo
            if self.buzzer:
                print("\n🔔 Buzzer Demonstration:")
                for i in range(3):
                    self.buzzer.beep(0.3)
                    time.sleep(0.3)
            
            # Motor demo
            if self.motor:
                print("\n⚙️  Motor Demonstration:")
                for speed in [30, 50, 70, 100]:
                    self.motor.set_speed(speed)
                    time.sleep(0.5)
                self.motor.turn_off()
            
            # Fan demo
            if self.fan:
                print("\n💨 Fan Demonstration:")
                self.fan.turn_on()
                time.sleep(2)
                self.fan.turn_off()
            
            # Light demo
            if self.light:
                print("\n💡 Light Demonstration:")
                self.light.turn_on()
                time.sleep(2)
                self.light.turn_off()
            
            # Relay demo
            if self.relay:
                print("\n🔌 Relay Demonstration:")
                self.relay.turn_all_on()
                time.sleep(2)
                self.relay.turn_all_off()
            
            print("\n✓ Device demonstration complete!\n")
            
        except KeyboardInterrupt:
            print("\n\n✓ Demonstration stopped")
        except Exception as e:
            print(f"\n✗ Error during demonstration: {e}")
    
    def continuous_monitoring(self, interval=5, log_data=True):
        """Continuously monitor all sensors"""
        print(f"\n📊 Starting continuous monitoring (interval: {interval}s)")
        print("Press Ctrl+C to stop\n")
        
        try:
            reading_count = 0
            while True:
                reading_count += 1
                data = self.read_all_sensors()
                self.display_readings(data)
                
                if log_data:
                    self.log_to_file(data)
                
                print(f"\nReading #{reading_count} - Next reading in {interval}s...")
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n\n✓ Monitoring stopped by user")
            print(f"Total readings taken: {reading_count}")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up all resources"""
        print("\n🔧 Cleaning up resources...")
        
        # Turn off all devices
        try:
            if self.led:
                self.led.turn_off()
        except:
            pass
        
        try:
            if self.buzzer:
                self.buzzer.turn_off()
        except:
            pass
        
        try:
            if self.motor:
                self.motor.cleanup()
        except:
            pass
        
        try:
            if self.fan:
                self.fan.turn_off()
        except:
            pass
        
        try:
            if self.light:
                self.light.turn_off()
        except:
            pass
        
        try:
            if self.led_strip:
                self.led_strip.turn_all_off()
        except:
            pass
        
        # Close sensors
        try:
            if self.sensors.get('dust'):
                self.sensors['dust'].cleanup()
        except:
            pass
        
        try:
            if self.sensors.get('ultrasonic'):
                self.sensors['ultrasonic'].cleanup()
        except:
            pass
        
        # GPIO cleanup
        try:
            GPIO.cleanup()
            print("✓ GPIO cleanup complete")
        except Exception as e:
            print(f"✗ GPIO cleanup error: {e}")


# ============================================================================
# MAIN PROGRAM
# ============================================================================

def print_menu():
    """Print interactive menu"""
    print("\n" + "=" * 60)
    print("HARDWARE CONTROL MENU")
    print("=" * 60)
    print("\n1. Read all sensors (single reading)")
    print("2. Start continuous monitoring")
    print("3. Run device demonstration")
    print("4. Control LED")
    print("5. Control Buzzer")
    print("6. Control Motor")
    print("7. Control Fan")
    print("8. Control Light")
    print("9. Control Relay (Fan + Light)")
    print("0. Exit")
    print("\n" + "-" * 60)


def main():
    """Main program"""
    print("\n" + "=" * 60)
    print("COMPREHENSIVE RASPBERRY PI HARDWARE SYSTEM")
    print("Multi-Sensor & Multi-Device Integration")
    print("=" * 60)
    
    try:
        # Initialize system
        system = HardwareSystem(enable_led=True, enable_sensors=True)
        
        while True:
            print_menu()
            choice = input("Enter your choice (0-9): ").strip()
            
            if choice == '0':
                print("\n✓ Exiting system...")
                break
            
            elif choice == '1':
                print("\n📊 Taking sensor reading...")
                data = system.read_all_sensors()
                system.display_readings(data)
            
            elif choice == '2':
                try:
                    interval = int(input("Enter reading interval (seconds, default 5): ") or "5")
                except ValueError:
                    interval = 5
                log = input("Log to file? (y/n, default y): ").lower() != 'n'
                system.continuous_monitoring(interval=interval, log_data=log)
            
            elif choice == '3':
                system.demo_all_devices()
            
            elif choice == '4':
                if system.led:
                    sub = input("LED: (1)On (2)Off (3)Toggle: ").strip()
                    if sub == '1':
                        system.led.turn_on()
                    elif sub == '2':
                        system.led.turn_off()
                    elif sub == '3':
                        system.led.toggle()
                else:
                    print("✗ LED not available")
            
            elif choice == '5':
                if system.buzzer:
                    sub = input("Buzzer: (1)Beep (2)On (3)Off: ").strip()
                    if sub == '1':
                        system.buzzer.beep()
                    elif sub == '2':
                        system.buzzer.turn_on()
                    elif sub == '3':
                        system.buzzer.turn_off()
                else:
                    print("✗ Buzzer not available")
            
            elif choice == '6':
                if system.motor:
                    try:
                        speed = int(input("Motor speed (0-100): "))
                        system.motor.set_speed(max(0, min(100, speed)))
                    except ValueError:
                        print("✗ Invalid input")
                else:
                    print("✗ Motor not available")
            
            elif choice == '7':
                if system.fan:
                    sub = input("Fan: (1)On (2)Off: ").strip()
                    if sub == '1':
                        system.fan.turn_on()
                    elif sub == '2':
                        system.fan.turn_off()
                else:
                    print("✗ Fan not available")
            
            elif choice == '8':
                if system.light:
                    sub = input("Light: (1)On (2)Off: ").strip()
                    if sub == '1':
                        system.light.turn_on()
                    elif sub == '2':
                        system.light.turn_off()
                else:
                    print("✗ Light not available")
            
            elif choice == '9':
                if system.relay:
                    sub = input("Relay: (1)On (2)Off: ").strip()
                    if sub == '1':
                        system.relay.turn_all_on()
                    elif sub == '2':
                        system.relay.turn_all_off()
                else:
                    print("✗ Relay not available")
            
            else:
                print("✗ Invalid choice")
        
        system.cleanup()
        return 0
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
