#!/usr/bin/env python2.7

# Generic TCP Server for iSpindel (https://github.com/universam1/iSpindel)
# Version: 1.0.1
# Now Supports Firmware 5.0.1
# Pre-Configured for Ready-to-Use Raspbian Image
#
# Receives iSpindel data as JSON via TCP socket and writes it to a CSV file, Database and/or Ubidots
# This is my first Python script ever, so please bear with me for now.
# Stephan Schreiber <stephan@sschreiber.de>, 2017-03-15

from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
from datetime import datetime
import thread
import json

# CONFIG Start

# General
DEBUG = 0                               # Set to 1 to enable debug output on console
PORT = 9501                             # TCP Port to listen to
HOST = '0.0.0.0'                        # Allowed IP range. Leave at 0.0.0.0 to allow connections from anywhere
CELSIUS = 1                             # Set to 1 to log temperature in Celcius

# CSV
CSV = 0                                 # Set to 1 if you want CSV (text file) output
OUTPATH = '/home/brewpi/iSpindel/'      # CSV output file path; filename will be name_id.csv
DELIMITER = ','                         # CSV delimiter (normally use ; for Excel)
NEWLINE='\n'                          # newline (\r\n for windows clients)
DATETIME = 1                            # Leave this at 1 to include Excel compatible timestamp in CSV

# Feed to BrewPI
BPI = 1                                 # Set to 1 if you want CSV (text file) output
OUTPATHPI = '/var/www/html/data/iSpindel/'              # CSV output file path; filename will be name_id.csv
DELIMITER = ','                        # CSV delimiter (normally use ; for Excel)
DATETIMEPI = 0
NEWLINE='\n'                          # newline (\r\n for windows clients)

# Ubidots Forwarding (using existing account)
UBIDOTS = 1                                     # change to 1 to enable output to ubidots and enter your token below
UBI_TOKEN = 'tokentokentokentokentoken'    # ubidots token (get this by registering with ubidots.com and then enter it here)

# ADVANCED
ENABLE_ADDCOLS = 0                              # Enable dynamic columns (configure pre-defined in lines 128-129)

# CONFIG End

ACK = chr(6)            # ASCII ACK (Acknowledge)
NAK = chr(21)           # ASCII NAK (Not Acknowledged)
BUFF = 1024             # Buffer Size (greatly exaggerated for now)

def dbgprint(s):
    if DEBUG == 1: print(s)

def handler(clientsock,addr):
    inpstr = ''
    success = False
    spindle_name = ''
    spindle_id = ''
    angle = 0.0
    temperature = 0.0
    battery = 0.0
    gravity = 0.0
    while 1:
        data = clientsock.recv(BUFF)
        if not data: break  # client closed connection
        dbgprint(repr(addr) + ' received:' + repr(data))
        if "close" == data.rstrip():
            clientsock.send(ACK)
            dbgprint(repr(addr) + ' ACK sent. Closing.')
            break   # close connection
        try:
            inpstr += str(data.rstrip())
            if inpstr[0] != "{" :
                clientsock.send(NAK)
                dbgprint(repr(addr) + ' Not JSON.')
                break # close connection
            dbgprint(repr(addr) + ' Input Str is now:' + inpstr)
            if inpstr.find("}") != -1 :
                jinput = json.loads(inpstr)
                spindle_name = jinput['name']
                spindle_id = jinput['ID']
                angle = jinput['angle']
                if CELSIUS == 1:
                        temperature = jinput['temperature']
                else:
                        temperature = (jinput['temperature'] * 1.8) + 32
                battery = jinput['battery']
                try:
                   gravity = jinput['gravity']
                except:
                   # probably using old firmware < 5.x
                   gravity = 0
                # looks like everything went well :)
                clientsock.send(ACK)
                success = True
                dbgprint(repr(addr) + ' ' + spindle_name + ' (ID:' + spindle_id + ') : Data received OK.')
                break # close connection
        except Exception as e:
            # something went wrong
            # traceback.print_exc() # too verbose, so let's do this instead:
            dbgprint(repr(addr) + ' Error: ' + str(e))
            clientsock.send(NAK)
            dbgprint(repr(addr) + ' NAK sent.')
            break # close connection server side after non-success
    clientsock.close()
    dbgprint(repr(addr) + " - closed connection") #log on console

    if success :
        # We have the complete spindle data now, so let's make it available
        if CSV == 1:
            #dbgprint(repr(addr) + ' - writing CSV')
            try:
                filename = OUTPATH + spindle_name + '_' + spindle_id + '.csv'
                with open(filename, 'a') as csv_file:
                        # a - append
                    # this would sort output. But we do not want that...
                    # import csv
                    # csvw = csv.writer(csv_file, delimiter=DELIMITER)
                    # csvw.writerow(jinput.values())
                    outstr = ''
                    outstr += spindle_name + DELIMITER
                    outstr += spindle_id + DELIMITER
                    outstr += str(angle) + DELIMITER
                    outstr += str(temperature) + DELIMITER
                    outstr += str(battery) + DELIMITER
                    outstr += str(gravity)
                    if DATETIME == 1:
                        cdt = datetime.now()
                        outstr += DELIMITER + cdt.strftime('%x %X')
                    outstr += NEWLINE
                    csv_file.writelines(outstr)
                    dbgprint(repr(addr) + ' - CSV data written.')
            except Exception as e:
                dbgprint(repr(addr) + ' CSV Error: ' + str(e))


        if BPI == 1:
            #dbgprint(repr(addr) + ' - writing CSV')
            try:
                filenamepi = OUTPATHPI +  'SpinData.csv'
                with open(filenamepi, 'w') as csv_file_bpi:
                        # a - append
                    # this would sort output. But we do not want that...
                    # import csv
                    # csvw = csv.writer(csv_file, delimiter=DELIMITER)
                    # csvw.writerow(jinput.values())
                    outstr = ''
                    if DATETIMEPI == 1:
                        cdt = datetime.now()
                        outstr +=  cdt.strftime('%x %X')
                    outstr += DELIMITER + str(gravity) + DELIMITER
                    outstr += str(battery) + DELIMITER
                    outstr += str(temperature)
                    outstr += NEWLINE
                    csv_file_bpi.writelines(outstr)
                    dbgprint(repr(addr) + ' - CSV data written.')
            except Exception as e:
                dbgprint(repr(addr) + ' CSV Error: ' + str(e))

        if UBIDOTS == 1:
            try:
                dbgprint(repr(addr) + ' - sending to ubidots')
                import urllib2
                outdata = {
                    'tilt' : angle,
                    'temperature' : temperature,
                    'battery' : battery,
                    'gravity' : gravity
                }
                out = json.dumps(outdata)
                dbgprint(repr(addr) + ' - sending: ' + out)
                url = 'http://things.ubidots.com/api/v1.6/devices/' + spindle_name + '?token=' + UBI_TOKEN
                req = urllib2.Request(url)
                req.add_header('Content-Type', 'application/json')
                req.add_header('User-Agent', spindle_name)
                response = urllib2.urlopen(req, out)
                dbgprint(repr(addr) + ' - received: ' + str(response))
            except Exception as e:
                dbgprint(repr(addr) + ' Ubidots Error: ' + str(e))


def main():
    ADDR = (HOST, PORT)
    serversock = socket(AF_INET, SOCK_STREAM)
    serversock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    serversock.bind(ADDR)
    serversock.listen(5)
    while 1:
        dbgprint('waiting for connection... listening on port: ' + str(PORT))
        clientsock, addr = serversock.accept()
        dbgprint('...connected from: ' + str(addr))
        thread.start_new_thread(handler, (clientsock, addr))

if __name__ == "__main__":
    main()
