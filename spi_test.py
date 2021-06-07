import spidev
import sys
import time
import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False) 
spi = spidev.SpiDev()
spi.open(0, 0)

GPIO.setup(5, GPIO.OUT)
GPIO.setup(6, GPIO.IN)

GPIO.output(5, GPIO.LOW)


# Settings 
spi.max_speed_hz = 3900000
spi.mode = 0b00
spi.bits_per_word = 8
spi.no_cs = False
spi.lsbfirst = False

frame_size = 55
to_send = []

for i in range(0,frame_size):
  to_send.append(i)
  

if __name__ == '__main__':
    
    while(GPIO.input(6)==False):
      GPIO.output(5, GPIO.HIGH)
      time.sleep(0.01) 
      GPIO.output(5, GPIO.LOW)
      
    GPIO.output(5, GPIO.HIGH)
    time.sleep(0.01) 
    GPIO.output(5, GPIO.LOW)
    
    print("STM32 Alive")
    try:
      while True:
      
        if(GPIO.input(6)==True):
          GPIO.output(5, GPIO.HIGH)
          time.sleep(0.01) 
          GPIO.output(5, GPIO.LOW)   
                 
        spi.writebytes(to_send)       
        read = spi.readbytes(frame_size)
        print(read)
        time.sleep(0.1) 
    except KeyboardInterrupt:
        GPIO.cleanup()
        spi.close() 
        sys.exit(0)  
