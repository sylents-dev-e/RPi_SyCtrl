import spidev
import sys
import time
import RPi.GPIO as GPIO
import struct
import csv
from datetime import datetime
import os.path
from os.path import isfile, join
from os import listdir
import re


# def extract_number(f):
#    s = re.findall("(\d+).csv", f)
#    return (int(s[0]) if s else -1, f)


#---------- File Settings ----------#
dirName = "spidata"
filename = "spidata_"

#---------- SPI Settings ----------#
spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 3900000
#BCM2835_SPI_CLOCK_DIVIDER_32768 = 32768,   ///< 32768 = 131.072us = 7.629394531kHz
#BCM2835_SPI_CLOCK_DIVIDER_16384 = 16384,   ///< 16384 = 65.536us = 15.25878906kHz
#BCM2835_SPI_CLOCK_DIVIDER_8192  = 8192,    ///< 8192 = 32.768us = 30/51757813kHz
#BCM2835_SPI_CLOCK_DIVIDER_4096  = 4096,    ///< 4096 = 16.384us = 61.03515625kHz
#BCM2835_SPI_CLOCK_DIVIDER_2048  = 2048,    ///< 2048 = 8.192us = 122.0703125kHz
#BCM2835_SPI_CLOCK_DIVIDER_1024  = 1024,    ///< 1024 = 4.096us = 244.140625kHz
#BCM2835_SPI_CLOCK_DIVIDER_512   = 512,     ///< 512 = 2.048us = 488.28125kHz
#BCM2835_SPI_CLOCK_DIVIDER_256   = 256,     ///< 256 = 1.024us = 976.5625MHz
#BCM2835_SPI_CLOCK_DIVIDER_128   = 128,     ///< 128 = 512ns = = 1.953125MHz
#BCM2835_SPI_CLOCK_DIVIDER_64    = 64,      ///< 64 = 256ns = 3.90625MHz
#BCM2835_SPI_CLOCK_DIVIDER_32    = 32,      ///< 32 = 128ns = 7.8125MHz
#BCM2835_SPI_CLOCK_DIVIDER_16    = 16,      ///< 16 = 64ns = 15.625MHz
#BCM2835_SPI_CLOCK_DIVIDER_8     = 8,       ///< 8 = 32ns = 31.25MHz
#BCM2835_SPI_CLOCK_DIVIDER_4     = 4,       ///< 4 = 16ns = 62.5MHz
#BCM2835_SPI_CLOCK_DIVIDER_2     = 2,       ///< 2 = 8ns = 125MHz, fastest you can get
#BCM2835_SPI_CLOCK_DIVIDER_1     = 1,       ///< 1 = 262.144us = 3.814697260kHz, same as
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
spi_cmd_data_no_file_write = 512  # 0x0200
spi_cmd_data_file_write = 513     # 0x0201

#---------- Transmission list ----------#
spi_tx_frame = []
spi_payload = []

# create payload ramp
for i in range(0, spi_payload_size):
    spi_payload.append(i)


if __name__ == '__main__':

    # test if directory exists
    if not os.path.exists(dirName):
        os.makedirs(dirName)
        print("Directory", dirName,  "created ")
#    else:
#        print("Directory", dirName,  "exists")

    # list all files
    onlyfiles = [f for f in listdir(dirName) if isfile(join(dirName, f))]
#    print(onlyfiles)
#    print(max(onlyfiles, key=extract_number))
    max = 0
    for file in onlyfiles:
        # assuming filename is "filexxx.txt"
        num = int(re.search(filename+'(\d*).csv', file).group(1))
        # compare num to previous max, e.g.
        max = num if num > max else max  # set max = 0 before for-loop
    nextnum = max+1
    newfilename = filename + str(nextnum) + '.csv'

    print("Filename:", newfilename)

#    sys.exit(0)

    #---------- ALIVE PING ----------#
    while(GPIO.input(6) == False):  # False
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

    # check if file exists

    #filename = 'spidata/test_data.csv'
    #filename = "{n}_{ts:%H_%M_%S}.csv".format(n=name, ts=datetime.now())

    data_file = open('./'+dirName+'/'+newfilename, 'w+', newline='')
    print(data_file)
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
        
        # check in every iteration the alive pins
        if(GPIO.input(6)!= True):
          GPIO.output(5, GPIO.HIGH)
          time.sleep(0.1)
          GPIO.output(5, GPIO.LOW)

        # filling the SPI transmission frame
        spi_tx_frame.append(spi_start_byte1)
        spi_tx_frame.append(spi_start_byte2)
        spi_tx_frame.append(spi_payload_size)
        spi_tx_frame.extend(spi_payload)
        spi_tx_frame.append(spi_crc_dummy)
        spi_tx_frame.append(spi_end_byte1)
        spi_tx_frame.append(spi_end_byte2)

        # write the SPI bytes
        #spi.writebytes(spi_tx_frame)

        spi_rx_frame = spi.xfer2(spi_tx_frame)

        # read the SPI bytes
        #spi_rx_frame = spi.readbytes(spi_frame_size)

        # check the SPI start and stopbytes
        if((spi_rx_frame[0] == spi_start_byte1) and (spi_rx_frame[1] == spi_start_byte2)
                  and (spi_rx_frame[spi_frame_size-2] == spi_end_byte1) and (spi_rx_frame[spi_frame_size-1] == spi_end_byte2)):

          # check the SPI payload size and parse the SPI frame
          if((spi_rx_frame[2]) == spi_payload_size):

            # parsing the single bytes from SPI into byte arrays
            command_bytearray = bytearray(
                [spi_rx_frame[spi_payloadoffset_cmd], spi_rx_frame[spi_payloadoffset_cmd+1]])

            timestamp_bytearray = bytearray([spi_rx_frame[spi_payloadoffset_data], spi_rx_frame[spi_payloadoffset_data+1],
              spi_rx_frame[spi_payloadoffset_data+2], spi_rx_frame[spi_payloadoffset_data+3]])

            motorcurrent_bytearray = bytearray([spi_rx_frame[spi_payloadoffset_data+4], spi_rx_frame[spi_payloadoffset_data+5],
              spi_rx_frame[spi_payloadoffset_data+6], spi_rx_frame[spi_payloadoffset_data+7]])

            dutycycle_bytearray = bytearray([spi_rx_frame[spi_payloadoffset_data+8], spi_rx_frame[spi_payloadoffset_data+9]])

            amperehours_bytearray = bytearray([spi_rx_frame[spi_payloadoffset_data+10], spi_rx_frame[spi_payloadoffset_data+11],
              spi_rx_frame[spi_payloadoffset_data+12], spi_rx_frame[spi_payloadoffset_data+13]])

            watthours_bytearray = bytearray([spi_rx_frame[spi_payloadoffset_data+14], spi_rx_frame[spi_payloadoffset_data+15],
              spi_rx_frame[spi_payloadoffset_data+16], spi_rx_frame[spi_payloadoffset_data+17]])

            tempmosfet_bytearray = bytearray(
                [spi_rx_frame[spi_payloadoffset_data+18], spi_rx_frame[spi_payloadoffset_data+19]])

            tempmotor_bytearray = bytearray(
                [spi_rx_frame[spi_payloadoffset_data+20], spi_rx_frame[spi_payloadoffset_data+21]])
            
            batterycurrent_bytearray = bytearray([spi_rx_frame[spi_payloadoffset_data+22], spi_rx_frame[spi_payloadoffset_data+23],
              spi_rx_frame[spi_payloadoffset_data+24], spi_rx_frame[spi_payloadoffset_data+25]])         

            pid_bytearray = bytearray(
                [spi_rx_frame[spi_payloadoffset_data+26], spi_rx_frame[spi_payloadoffset_data+27]])

            batteryvoltage_bytearray = bytearray([spi_rx_frame[spi_payloadoffset_data+28], spi_rx_frame[spi_payloadoffset_data+29],
              spi_rx_frame[spi_payloadoffset_data+30], spi_rx_frame[spi_payloadoffset_data+31]])   

            
            
            loadcell_hx711_bytearray = bytearray([spi_rx_frame[spi_payloadoffset_data+34], spi_rx_frame[spi_payloadoffset_data+35]])

            # unpacking RX bytewise
            command_value = struct.unpack(">H", command_bytearray)
            timestamp_value = struct.unpack(">I", timestamp_bytearray)
            motorcurrent_value = struct.unpack(">f", motorcurrent_bytearray)
            dutycylce_value = struct.unpack(">H", dutycycle_bytearray)
            amperehours_value = struct.unpack(">I", amperehours_bytearray)
            watthours_value = struct.unpack(">I", watthours_bytearray)
            tempmosfet_value = struct.unpack(">H", tempmosfet_bytearray)
            tempmotor_value = struct.unpack(">H", tempmotor_bytearray)
            batterycurrent_value = struct.unpack(">f", batterycurrent_bytearray)
            pid_value = struct.unpack(">H", pid_bytearray)
            batteryvoltage_value = struct.unpack(">f", batteryvoltage_bytearray)
            joystick_i2c_x_value = struct.unpack(">b", bytearray([spi_rx_frame[spi_payloadoffset_data+32]]))
            joystick_i2c_y_value = struct.unpack(">b", bytearray([spi_rx_frame[spi_payloadoffset_data+33]]))
            loadcell_hx711_value = struct.unpack(">H", loadcell_hx711_bytearray)


            # check which command is send
            if(int(''.join(map(str, command_value))) == spi_cmd_data_no_file_write):
              #data_file.close()
              print("no file writing")
              print(type(spi_rx_frame[spi_payloadoffset_data+30]))
              print(command_value, timestamp_value, motorcurrent_value, dutycylce_value, amperehours_value, 
                watthours_value, tempmosfet_value, tempmotor_value, batterycurrent_value, pid_value,
                batteryvoltage_value, joystick_i2c_x_value, joystick_i2c_y_value, loadcell_hx711_value)
            elif(int(''.join(map(str, command_value))) == spi_cmd_data_file_write):
              csvwriter.writerow(command_value + timestamp_value + motorcurrent_value)
            else:
              dummy = 0   

          else:
            # error handling payload size
            dummy = 0
        else:
          # error handling incorrect start or stop
          dummy = 0

        

          # avoid overflow of 4096 bytes SPI buffer
        spi_tx_frame.clear()
        spi_rx_frame.clear()

            #result.write(str(command_value) + ";" + str(timestamp_value) + ";" + str(motorcurrent_value) + "\n")
            #csvwriter.writerow(command_value + timestamp_value + motorcurrent_value)

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