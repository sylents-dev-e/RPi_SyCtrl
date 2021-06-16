import spidev
import sys
import time
import RPi.GPIO as GPIO
import struct
import csv
from datetime import datetime

#---------- SPI Settings ----------#
spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 3900000
spi.mode = 0b00
spi.bits_per_word = 8
spi.no_cs = False
spi.lsbfirst = False

# SYNC pins
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False) 
GPIO.setup(5, GPIO.OUT)  
GPIO.setup(6, GPIO.IN)
GPIO.output(5, GPIO.LOW)

#---------- Constants ----------#
spi_frame_size = 54
spi_payload_size = 48
spi_start_byte1 = 85       # 0x55
spi_start_byte2 = 170      # 0xAA
spi_crc_dummy = 165        # 0xA5
spi_end_byte1 = 195        # 0xC3
spi_end_byte2 = 60         # 0x3C
spi_payloadoffset_cmd = 3
spi_payloadoffset_data = 5

#---------- Transmission list ----------#
spi_tx_frame = []
spi_payload = []

for i in range(0,spi_payload_size):
  spi_payload.append(i)
  

if __name__ == '__main__':
    
    #---------- ALIVE PING ----------#  
    while(GPIO.input(6)==False):
      GPIO.output(5, GPIO.HIGH)
      time.sleep(0.1) 
      GPIO.output(5, GPIO.LOW)
      
    GPIO.output(5, GPIO.HIGH)
    time.sleep(0.1) 
    GPIO.output(5, GPIO.LOW)
    
    print("STM32 Alive")

    #---------- FILE OPEN ----------#     
#    with open('testdata.csv', 'w', newline='') as csvfile:
#      spamwriter = csv.writer(csvfile, delimiter=' ',
#      quotechar='|', quoting=csv.QUOTE_MINIMAL)
    
    filename = 'Desktop/test_data.csv'
    #filename = "{n}_{ts:%H_%M_%S}.csv".format(n=name, ts=datetime.now())
    
    data_file = open(filename, 'w', newline='')
    now = datetime.now()
    time_base = now.strftime("%H%M%S\0")
    date_base = now.strftime("%d%m%Y\0")
    csvwriter = csv.writer(data_file, delimiter=',',
      quotechar='|', quoting=csv.QUOTE_MINIMAL)
        #result.write(timestamp + ";data1;data2;data3\n")
    csvwriter.writerow([time_base + date_base + '0'])

    #---------- ENDLESS LOOP ----------# 
    try:
        while True:
        
          if(GPIO.input(6)==True):
            GPIO.output(5, GPIO.HIGH)
            time.sleep(0.1) 
            GPIO.output(5, GPIO.LOW)   
          
          spi_tx_frame.append(spi_start_byte1)
          spi_tx_frame.append(spi_start_byte2)
          spi_tx_frame.append(spi_payload_size)
          spi_tx_frame.extend(spi_payload)
          spi_tx_frame.append(spi_crc_dummy)
          spi_tx_frame.append(spi_end_byte1)
          spi_tx_frame.append(spi_end_byte2)
                  
          spi.writebytes(spi_tx_frame)       
          spi_rx_frame = spi.readbytes(spi_frame_size)
          
          if((spi_rx_frame[0] == spi_start_byte1) and (spi_rx_frame[1] == spi_start_byte2)
              and (spi_rx_frame[spi_frame_size-2] == spi_end_byte1) and (spi_rx_frame[spi_frame_size-1] == spi_end_byte2)):        

            if((spi_rx_frame[2]) == spi_payload_size):
              command_bytearray = bytearray([spi_rx_frame[spi_payloadoffset_cmd], spi_rx_frame[spi_payloadoffset_cmd+1]])
              timestamp_bytearray = bytearray([spi_rx_frame[spi_payloadoffset_data], spi_rx_frame[spi_payloadoffset_data+1], 
                                spi_rx_frame[spi_payloadoffset_data+2], spi_rx_frame[spi_payloadoffset_data+3]])
              motorcurrent_bytearray = bytearray([spi_rx_frame[spi_payloadoffset_data+4], spi_rx_frame[spi_payloadoffset_data+5],
                                spi_rx_frame[spi_payloadoffset_data+6], spi_rx_frame[spi_payloadoffset_data+7]])
            
              # unpacking RX bytewise   
              command_value = struct.unpack(">H", command_bytearray)
              timestamp_value = struct.unpack(">I", timestamp_bytearray)
              motorcurrent_value = struct.unpack(">f", motorcurrent_bytearray)
              print(command_value, timestamp_value, motorcurrent_value)  
            else:
              #error handling payload size
              dummy = 0
          else:
            #error handling incorrect start or stop
            dummy = 0

          # avoid overflow of 4096 bytes SPI buffer
          spi_tx_frame.clear()
          spi_rx_frame.clear()
          
          #result.write(str(command_value) + ";" + str(timestamp_value) + ";" + str(motorcurrent_value) + "\n")
          csvwriter.writerow(command_value + timestamp_value + motorcurrent_value)
          

          time.sleep(0.1)
    except KeyboardInterrupt: 
      GPIO.cleanup()
      data_file.close()
      spi.close() 
      sys.exit(0) 
    except: 
      GPIO.cleanup()
      data_file.close()
      spi.close() 
      sys.exit(0) 
