import spidev
import sys
import time
spi = spidev.SpiDev()
spi.open(0, 0)

# Settings 
spi.max_speed_hz = 1000000
spi.mode = 0b00
spi.no_cs = False
to_send = [0x23, 0x03]

if __name__ == '__main__':
    try:
      while True:
        spi.writebytes(to_send)
        read = spi.readbytes(2)
        time.sleep(0.5)
        print(read)
    except KeyboardInterrupt:
        spi.close() 
        sys.exit(0)  
