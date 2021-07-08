"""
Packet XVR module on RPi. Transmitting Config and Receiving Status+Sensordata.
"""
import sys
import time
import struct
import csv
from datetime import datetime
import os.path
from os.path import isfile, join
from os import listdir
import re

import RPi.GPIO as GPIO
import spidev
import sypacket as syp

# def extract_number(f):p
#    s = re.findall("(\d+).csv", f)
#    return (int(s[0]) if s else -1, f)


#---------- File Settings ----------#
DIRNAME = "spidata"
FILEPRE = "spidata_"

#---------- SPI Settings ----------#
spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 3900000
# BCM2835_SPI_CLOCK_DIVIDER_32768 = 32768,   ///< 32768 = 131.072us = 7.629394531kHz
# BCM2835_SPI_CLOCK_DIVIDER_16384 = 16384,   ///< 16384 = 65.536us = 15.25878906kHz
# BCM2835_SPI_CLOCK_DIVIDER_8192  = 8192,    ///< 8192 = 32.768us = 30/51757813kHz
# BCM2835_SPI_CLOCK_DIVIDER_4096  = 4096,    ///< 4096 = 16.384us = 61.03515625kHz
# BCM2835_SPI_CLOCK_DIVIDER_2048  = 2048,    ///< 2048 = 8.192us = 122.0703125kHz
# BCM2835_SPI_CLOCK_DIVIDER_1024  = 1024,    ///< 1024 = 4.096us = 244.140625kHz
# BCM2835_SPI_CLOCK_DIVIDER_512   = 512,     ///< 512 = 2.048us = 488.28125kHz
# BCM2835_SPI_CLOCK_DIVIDER_256   = 256,     ///< 256 = 1.024us = 976.5625MHz
# BCM2835_SPI_CLOCK_DIVIDER_128   = 128,     ///< 128 = 512ns = = 1.953125MHz
# BCM2835_SPI_CLOCK_DIVIDER_64    = 64,      ///< 64 = 256ns = 3.90625MHz
# BCM2835_SPI_CLOCK_DIVIDER_32    = 32,      ///< 32 = 128ns = 7.8125MHz
# BCM2835_SPI_CLOCK_DIVIDER_16    = 16,      ///< 16 = 64ns = 15.625MHz
# BCM2835_SPI_CLOCK_DIVIDER_8     = 8,       ///< 8 = 32ns = 31.25MHz
# BCM2835_SPI_CLOCK_DIVIDER_4     = 4,       ///< 4 = 16ns = 62.5MHz
# BCM2835_SPI_CLOCK_DIVIDER_2     = 2,       ///< 2 = 8ns = 125MHz, fastest you can get
# BCM2835_SPI_CLOCK_DIVIDER_1     = 1,       ///< 1 = 262.144us = 3.814697260kHz, same as
spi.mode = 0b00
spi.bits_per_word = 8
spi.no_cs = False
spi.lsbfirst = False

# SYNC pins
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(syp.PIN_RPIALIVE, GPIO.OUT)
GPIO.setup(syp.PIN_STMALIVE, GPIO.IN)
GPIO.output(5, GPIO.LOW)

#---------- Constants ----------#
SPIFRMSIZE = 54
SPIPAYSIZE = 48
# SPISTARTB0 = 85                # 0x55
SPISTARTB0 = 0x55                   # 0x55
SPISTARTB1 = 0xAA                   # 0xAA
spi_crc_dummy = 0xA5                # 0xA5
spi_end_byte1 = 0xC3                # 0xC3
spi_end_byte2 = 0x3C                # 0x3C
spi_payloadoffset_cmd = 3
spi_payloadoffset_data = 5
# 0x0200 cmd stm sensordata sensordata from stm
spi_cmd_sensordata_nolog = 0x200
spi_cmd_sensordata_log = 0x0201     # 0x0201 cmd
spi_cmd_status = 0x0203             # 0x0203


#---------- Objects ----------#
class TxFrame:
    # default constructor:
    def __init__(self):
        self.tx_frame = bytearray(SPIFRMSIZE)
        # initialize tx frame

        self.tx_frame[0] = SPISTARTB0
        self.tx_frame[1] = SPISTARTB1
        self.tx_frame[2] = SPIPAYSIZE
        for i in range(0, SPIPAYSIZE):
            self.tx_frame[i+3] = i
        self.tx_frame[SPIPAYSIZE+3] = spi_crc_dummy
        self.tx_frame[SPIPAYSIZE+4] = spi_end_byte1
        self.tx_frame[SPIPAYSIZE+5] = spi_end_byte2

    def reinit(self):
        self.tx_frame[0] = SPISTARTB0
        self.tx_frame[1] = SPISTARTB1
        self.tx_frame[2] = SPIPAYSIZE
        for i in range(0, SPIPAYSIZE):
            self.tx_frame[i+3] = i
        self.tx_frame[SPIPAYSIZE+3] = spi_crc_dummy
        self.tx_frame[SPIPAYSIZE+4] = spi_end_byte1
        self.tx_frame[SPIPAYSIZE+5] = spi_end_byte2

    def print(self):
        print(self.tx_frame)

    def printhex(self):
        print(" ".join(hex(n) for n in self.tx_frame))

    def arr(self):
        self.tx_frame


#------------------------------#
if __name__ == '__main__':
    #------------------------------#

    old_command = bytearray([])
    fault_counter = 0

    if syp.DBG:
        print("---------- DEBUG MODE ----------")

    #---------- ALIVE PING ----------#
    print("Checking STM32 ALIVE on pin_"+str(syp.PIN_STMALIVE))
    while((GPIO.input(syp.PIN_STMALIVE) != syp.STM32_ALIVE) and not syp.DBG):
        # Waiting for STM32 coming to live
        GPIO.output(syp.PIN_RPIALIVE, GPIO.HIGH)
        time.sleep(syp.PINT)
        GPIO.output(syp.PIN_RPIALIVE, GPIO.LOW)

        # STM32 Alive Signal Detected
    GPIO.output(syp.PIN_RPIALIVE, GPIO.HIGH)
    time.sleep(syp.PINT)
    GPIO.output(syp.PIN_RPIALIVE, GPIO.LOW)

    print("Found STM32 is Alive")

    # prepare direcory and file
    # check if file exists
    # test if directory exists
    if not os.path.exists(DIRNAME):
        os.makedirs(DIRNAME)
        print("Directory", DIRNAME,  "created ")
    # list all files
    onlyfiles = [f for f in listdir(DIRNAME) if isfile(join(DIRNAME, f))]

    fmax = 0
    for file in onlyfiles:
        # assuming filename is "filexxx.txt"
        num = int(re.search(FILEPRE+'(\d*).csv', file).group(1))
        # compare num to previous max, e.g.
        fmax = num if num > fmax else fmax  # set max = 0 before for-loop
    nextnum = fmax+1

    filename = FILEPRE + str(nextnum) + '.csv'
    data_file = open('./'+DIRNAME+'/'+filename, 'w+', newline='')
    now = datetime.now()
    time_base = now.strftime("%H%M%S\0")
    date_base = now.strftime("%d%m%Y\0")
    csvwriter = csv.writer(data_file, delimiter=',',
        quotechar='|', quoting=csv.QUOTE_MINIMAL)
    csvwriter.writerow([time_base + date_base + '0'])

    print("Filename:", filename)

    # initialize txo tx framepacket object
    txo = TxFrame()
    if syp.DBG:
        print(" ".join(hex(n) for n in txo.tx_frame))

    #---------- ENDLESS CMD Processing Loop ----------#
    try:

        while True:

            # check in every iteration the alive pins
            # @jwa is this really neccessary ?
            if GPIO.input(syp.PIN_STMALIVE) != syp.STM32_ALIVE:
                # Waiting for STM32 becoming Alive Again
                # @todo add timeout counter
                GPIO.output(syp.PIN_RPIALIVE, GPIO.HIGH)
                time.sleep(syp.PINT)
                GPIO.output(syp.PIN_RPIALIVE, GPIO.LOW)

            
            # SEND and RECEIVE Data Frame
            if syp.DBG:
                print("spi_xfer "+str(len(txo.tx_frame)))
#                print(" ".join(hex(n) for n in txo.tx_frame))

            # Transmit Receive SPI Packet
            spi_rx_frame = spi.xfer2(txo.tx_frame)


            # check the Packet Format's start and stopbytes
            if((spi_rx_frame[syp.OFF_START] == SPISTARTB0) and (spi_rx_frame[syp.OFF_START+1] == SPISTARTB1)
               and (spi_rx_frame[SPIFRMSIZE-2] == spi_end_byte1) and (spi_rx_frame[SPIFRMSIZE-1] == spi_end_byte2)):

                # check the SPI payload size and parse the SPI frame
                if (spi_rx_frame[syp.OFF_PSIZE]) == SPIPAYSIZE:

                    # parsing the single bytes from SPI into byte arrays
                    command_bytearray = bytearray(
                        [spi_rx_frame[spi_payloadoffset_cmd], spi_rx_frame[spi_payloadoffset_cmd+1]])

                    timestamp_bytearray = bytearray([spi_rx_frame[spi_payloadoffset_data], spi_rx_frame[spi_payloadoffset_data+1],
                                                     spi_rx_frame[spi_payloadoffset_data+2], spi_rx_frame[spi_payloadoffset_data + syp.OFF_TIMESTAMP]])

                    motorcurrent_bytearray = bytearray([spi_rx_frame[spi_payloadoffset_data+4], spi_rx_frame[spi_payloadoffset_data+5],
                                                        spi_rx_frame[spi_payloadoffset_data+6], spi_rx_frame[spi_payloadoffset_data+7]])

                    dutycycle_bytearray = bytearray(
                        [spi_rx_frame[spi_payloadoffset_data+8], spi_rx_frame[spi_payloadoffset_data+9]])

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

                    loadcell_hx711_bytearray = bytearray(
                        [spi_rx_frame[spi_payloadoffset_data+34], spi_rx_frame[spi_payloadoffset_data+35]])

                    # unpacking RX bytewise
                    command_value = struct.unpack(">H", command_bytearray)
                    timestamp_value = struct.unpack(">I", timestamp_bytearray)
                    motorcurrent_value = struct.unpack(
                        ">f", motorcurrent_bytearray)
                    dutycylce_value = struct.unpack(">H", dutycycle_bytearray)
                    amperehours_value = struct.unpack(
                        ">I", amperehours_bytearray)
                    watthours_value = struct.unpack(">I", watthours_bytearray)
                    tempmosfet_value = struct.unpack(
                        ">H", tempmosfet_bytearray)
                    tempmotor_value = struct.unpack(">H", tempmotor_bytearray)
                    batterycurrent_value = struct.unpack(
                        ">f", batterycurrent_bytearray)
                    pid_value = struct.unpack(">H", pid_bytearray)
                    batteryvoltage_value = struct.unpack(
                        ">f", batteryvoltage_bytearray)
                    joystick_i2c_x_value = struct.unpack(
                        ">b", bytearray([spi_rx_frame[spi_payloadoffset_data+32]]))
                    joystick_i2c_y_value = struct.unpack(
                        ">b", bytearray([spi_rx_frame[spi_payloadoffset_data+33]]))
                    loadcell_hx711_value = struct.unpack(
                        ">H", loadcell_hx711_bytearray)

                    

                    # check rcv command type
                    # case: Sensordata packet -no_logging
                    if int(''.join(map(str, command_value))) == spi_cmd_sensordata_nolog:
                        # data_file.close()
                            
                        
                        # close data file if it has been open for logging
                        if (data_file.closed == False):                            
                            data_file.close()

                        if syp.DBG:
                            print("-no_log")
                            print(type(spi_rx_frame[spi_payloadoffset_data+30]))
                            print(command_value, timestamp_value, motorcurrent_value, dutycylce_value, amperehours_value,
                                  watthours_value, tempmosfet_value, tempmotor_value, batterycurrent_value, pid_value,
                                  batteryvoltage_value, joystick_i2c_x_value, joystick_i2c_y_value, loadcell_hx711_value)

                    # case: Sensordata packet -logging
                    elif int(''.join(map(str, command_value))) == spi_cmd_sensordata_log:

                        if syp.DBG:
                            print(old_command)

                        # Reopen File if closed
                        if (data_file.closed == True):

                            print("here")
                            # list all files
                            onlyfiles = [f for f in listdir(DIRNAME) if isfile(join(DIRNAME, f))]

                            fmax = 0
                            for file in onlyfiles:
                                # assuming filename is "filexxx.txt"
                                num = int(re.search(FILEPRE+'(\d*).csv', file).group(1))
                                # compare num to previous max, e.g.
                                fmax = num if num > fmax else fmax  # set max = 0 before for-loop
                            nextnum = fmax+1

                            filename = FILEPRE + str(nextnum) + '.csv'
                            data_file = open('./'+DIRNAME+'/' + filename, 'w+', newline='')
                            now = datetime.now()
                            time_base = now.strftime("%H%M%S\0")
                            date_base = now.strftime("%d%m%Y\0")
                            csvwriter = csv.writer(data_file, delimiter=',',
                                quotechar='|', quoting=csv.QUOTE_MINIMAL)
                            csvwriter.writerow([time_base + date_base + '0'])
                            print("Filename:", filename)
                        
                        # append data to .csv
                        csvwriter.writerow(command_value + timestamp_value + motorcurrent_value +
                                dutycylce_value + amperehours_value + watthours_value + tempmosfet_value +
                                tempmotor_value + tempmotor_value + batterycurrent_value + pid_value +
                                batteryvoltage_value + joystick_i2c_x_value + joystick_i2c_y_value +
                                loadcell_hx711_value)
 

                    # 3. case: status received from stm32
                    else:
                        print("Status")

                    old_command = command_value
                else:
                    # error handling payload size
                    dummy = 0
                    fault_counter += 1
                    print("F101: RX SPI unexpected size, fc: "+str(fault_counter))
            else:
                # error handling incorrect start or stop
                dummy = 0
                fault_counter += 1
                print("F102: Rx SPI missing delimiters, fc: "+str(fault_counter))

            # avoid overflow of 4096 bytes SPI buffer
            # txf.clear()
            spi_rx_frame.clear()

            time.sleep(0.25)
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
