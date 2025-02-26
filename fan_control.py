import RPi.GPIO as GPIO
import sys, traceback, json
from time import sleep
from re import findall
from datetime import datetime
from subprocess import check_output
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from RPLCD.i2c import CharLCD

interval = 1

def get_temp():
    temp = check_output(["vcgencmd", "measure_temp"]).decode()
    temp = float(findall(r'\d+\.\d+', temp)[0])
    return temp

def count_pulse(channel):
    global pulse_count
    pulse_count += 1

def read_json(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)
    
def update_lcd_cell(lcd, row, col, text):
    lcd.cursor_pos = (row, col)
    lcd.write_string(text)

def set_backlight_by_time(time_1, time_2, mode):
    time_1 = datetime.strptime(time_1, "%H:%M").time()
    time_2 = datetime.strptime(time_2, "%H:%M").time()
    now = datetime.now().time()
    if mode == "day": lcd.backlight_enabled = time_1 <= now < time_2
    elif mode == "night": lcd.backlight_enabled = not (time_1 <= now < time_2)
    elif mode == "on": lcd.backlight_enabled = True
    elif mode == "off": lcd.backlight_enabled = False

config = read_json("config.json")
influxdb_config = read_json(config['influxdb_config_path'])
client = InfluxDBClient(url=influxdb_config['influxdb_url'], token=influxdb_config['influxdb_token'])
write_api = client.write_api(write_options=SYNCHRONOUS)

def write_current_data(temp, pinState, rpm):
    fan_state = 1 if pinState else 0
    point = Point("fan_status").tag("location", "raspberry_pi").field("temperature", temp).field("fan_state", fan_state).field("rpm", rpm)
    write_api.write(bucket=config['influxdb_bucket'], org=config['influxdb_org'], record=point)

has_lcd = True
try:
    lcd = CharLCD('PCF8574', 0x27)
    lcd.clear()
    lcd.backlight_enabled = True
    lcd.write_string('Fan Control')
    lcd.cursor_pos = (1, 0)
    lcd.write_string('Starting...')
    sleep(2)
except:
    has_lcd = False

try:
    settings = read_json("settings.json")
    tempOn = int(settings.get('tempOn', 50))
    tempOff = int(settings.get('tempOff', 40))
    mode = settings['mode']
    
    controlPin = 14
    pinState = False

    tachPin = 12
    pulse_count = 0
    rpm = float(0)
    
    prev_temp = 0
    prev_fan_state = None
    prev_rpm = -1
    prev_mode = ""
    
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(controlPin, GPIO.OUT, initial=0)
    GPIO.setup(tachPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.add_event_detect(tachPin, GPIO.FALLING, callback=count_pulse)

    if has_lcd:
        lcd.clear()
        lcd.cursor_pos = (0, 0)
        lcd.write_string(f'Temp:     Fan:   ')
        lcd.cursor_pos = (1, 0)
        lcd.write_string(f'RPM:          ')

    while True:
        settings = read_json("settings.json")
        tempOn = int(settings.get('tempOn', 50))
        tempOff = int(settings.get('tempOff', 40))
        mode = settings['mode']

        backlight_time_1 = settings.get('backlight_time_1', '7:00')
        backlight_time_2 = settings.get('backlight_time_2', '22:00')
        backlight_mode = settings.get('backlight_mode', 'on')

        temp = get_temp()
        pulse_count = 0

        if mode == 'smart':
            if temp > tempOn and not pinState or temp < tempOff and pinState:
                pinState = not pinState
                GPIO.output(controlPin, pinState)
        elif mode == 'normal':
            if temp > tempOn:
                pinState = True
                GPIO.output(controlPin, pinState)
            elif temp < tempOn:
                pinState = False
                GPIO.output(controlPin, pinState)
        else:
            pinState = True
            GPIO.output(controlPin, pinState)

        write_current_data(temp, pinState, rpm)
        
        if has_lcd:
            set_backlight_by_time(backlight_time_1, backlight_time_2, backlight_mode)
            
            if abs(temp - prev_temp) >= 0.1:
                update_lcd_cell(lcd, 0, 5, f'{temp:4.1f}')
                prev_temp = temp

            fan_state_text = 'ON ' if pinState else 'OFF'
            if prev_fan_state != pinState:
                update_lcd_cell(lcd, 0, 14, fan_state_text)
                prev_fan_state = pinState
            
            if abs(rpm - prev_rpm) >= 1:
                update_lcd_cell(lcd, 1, 4, f'{rpm:4.0f}')
                prev_rpm = rpm
            
            if prev_mode != mode:
                update_lcd_cell(lcd, 1, 9, f'{mode:>6}')
                prev_mode = mode
        
        print(f"Temperature: {temp}°C, Fan State: {'On' if pinState else 'Off'}, RPM: {rpm}, Mode: {mode}, TempOn: {tempOn}, TempOff: {tempOff}")
        sleep(1)
        rpm = (pulse_count / 2) * (60 / interval)
        
except KeyboardInterrupt:
    print("Exit pressed Ctrl+C")
except Exception as e:
    print("Other Exception")
    print("--- Start Exception Data:")
    traceback.print_exc(limit=2, file=sys.stdout)
    print("--- End Exception Data:")
finally:
    print("CleanUp")
    if 'lcd' in locals() and has_lcd:
        lcd.clear()
        lcd.write_string('Shutting down...')
        sleep(1)
        lcd.clear()
    GPIO.cleanup()
    print("End of program")
