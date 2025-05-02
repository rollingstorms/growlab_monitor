import time
from smbus2 import SMBus, i2c_msg

def read(bus_number=1, address=0x44, meas_cmd=0xFD, delay=0.02):
    """
    Trigger a measurement on the SHT40 and return (temperature_C, humidity_%RH).
    
    Args:
      bus_number: I²C bus (1 on a Raspberry Pi Zero/3/4/5)
      address:    I²C address of the SHT40 (default 0x44)
      meas_cmd:   Measurement command (0xFD = high-repeat, no clock-stretch)
      delay:      Seconds to wait for the conversion (~15 ms minimum)
      
    Returns:
      (temperature_celsius, relative_humidity_percent)
    """
    with SMBus(bus_number) as bus:
        # 1) send measure command
        write = i2c_msg.write(address, [meas_cmd])
        read  = i2c_msg.read(address, 6)
        bus.i2c_rdwr(write)
        
        # 2) wait for conversion
        time.sleep(delay)
        
        # 3) read 6 bytes back
        bus.i2c_rdwr(read)
        data = list(read)

    # parse raw values
    t_raw = (data[0] << 8) | data[1]
    h_raw = (data[3] << 8) | data[4]

    # convert per datasheet
    temperature = -45 + (175 * t_raw / 65535)
    humidity    = 100 * (h_raw / 65535)

    return temperature, humidity
