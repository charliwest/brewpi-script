#!/usr/bin/env python2.7

# Version: 1.3.1
# New: Forward data to another instance of this script or any other JSON recipient
# New: Support changes in firmware >= 5.4.0 (ID now transmitted as Integer)
#
# Generic TCP Server for iSpindel (https://github.com/universam1/iSpindel)
# Receives iSpindel data as JSON via TCP socket and writes it to a CSV file, Database and/or forwards it
#
# Stephan Schreiber <stephan@sschreiber.de>, 2017-02-02 - 2017-08-31
#

from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
from datetime import datetime
import thread
import json

# CONFIG Start

# General
DEBUG = 1                               # Set to 1 to enable debug output on console (usually devs only)
PORT = 9501                             # TCP Port to listen to (to be used in iSpindle config as well)
HOST = '0.0.0.0'                        # Allowed IP range. Leave at 0.0.0.0 to allow connections from anywhere
CELSIUS = 1                             # Set to 1 to log temperature in Celcius

# CSV
CSV = 1                                 # Set to 1 if you want CSV (text file) output
OUTPATH = '/home/brewpi/iSpindel/'      # CSV output file path; filename will be name_id.csv
DELIMITER = ';'                         # CSV delimiter (normally use ; for Excel)
NEWLINE='\n'                          # newline (\r\n for windows clients)
DATETIME = 0                            # Leave this at 1 to include Excel compatible timestamp in CSV

# Feed to BrewPI
BPI = 1                                 # Set to 1 if you want CSV (text file) output
OUTPATHPI = '/var/www/html/data/iSpindel/'  # CSV output file path; filename will be name_id.csv
DELIMITER = ','                        # CSV delimiter (normally use ; for Excel)
DATETIMEPI = 0
NEWLINE='\n'                          # newline (\r\n for windows clients)

# Ubidots (using existing account)
UBIDOTS = 0                                     # 1 to enable output to ubidots
UBI_TOKEN = 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'    # ubidots token, see manual or ubidots.com

# Forward to public server or other relay (i.e. another instance of this script)
FORWARD = 0
# FORWARDADDR = 'ispindle.de'
# FORWARDPORT = 9501
FORWARDADDR = '192.168.2.21'
FORWARDPORT = 9501

# ADVANCED
ENABLE_ADDCOLS = 0                              # Enable dynamic columns (do not use this unless you're a developer)

# CONFIG End

ACK = chr(6)            # ASCII ACK (Acknowledge)
NAK = chr(21)           # ASCII NAK (Not Acknowledged)
BUFF = 1024             # Buffer Size (greatly exaggerated for now)

def dbgprint(s):
    if DEBUG == 1: print(str(s))

def handler(clientsock,addr):
    inpstr = ''
    success = 0
    spindle_name = ''
    spindle_id = ''
    angle = 0.0
    temperature = 0.0
    battery = 0.0
    gravity = 0.0
    user_token = ''
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
                   # older firmwares < 5.0.1 are not transmitting this parameter
                   gravity = 0.0
                try:
                    # get user token for connection to ispindle.de public server
                    user_token = jinput['token']
                except:
                    # older firmwares < 5.         4 or field not filled in
                    user_token = ''
                # looks like everything went well :)
                clientsock.send(ACK)
                dbgprint(repr(addr) + ' ' + spindle_name + ' (ID:' + str(spindle_id) + ') : Data received OK.')
                success = 1
                break # close connection
        except Exception as e:
            # something went wrong
            # traceback.print_exc() # this would be too verbose, so let's do this instead:
            dbgprint(repr(addr) + ' Error: ' + str(e))
            clientsock.send(NAK)
            dbgprint(repr(addr) + ' NAK sent.')
            break # close connection server side after non-success
    clientsock.close()
    dbgprint(repr(addr) + " - closed connection") #log on console

    if success == 1:
        # We have the complete spindle data now, so let's make it available
        if CSV == 1:
            dbgprint(repr(addr) + ' - writing CSV')
            try:
                filename = OUTPATH + spindle_name + str(spindle_id) + '.csv'
                with open(filename, 'a') as csv_file:
                    # this would sort output. But we do not want that...
                    # import csv
                    # csvw = csv.writer(csv_file, delimiter=DELIMITER)
                    # csvw.writerow(jinput.values())
                    outstr = ''
                    outstr += str(spindle_name) + DELIMITER
                    outstr += str(spindle_id) + DELIMITER
                    outstr += str(angle) + DELIMITER
                    outstr += str(temperature) + DELIMITER
                    outstr += str(battery) + DELIMITER
                    outstr += str(gravity) + DELIMITER
                    outstr += user_token
                    if DATETIME == 1:
                        cdt = datetime.now()
                        outstr += DELIMITER + cdt.strftime('%x %X')
                    outstr += NEWLINE
                    csv_file.writelines(outstr)
                    dbgprint(repr(addr) + ' - CSV data written.')
            except Exception as e:
                dbgprint(repr(addr) + ' CSV Error: ' + str(e))

        if BPI == 1:
            dbgprint(repr(addr) + ' - writing CSV')
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
                        outstr +=  cdt.strftime('%x %X') + DELIMITER
                    outstr += str(gravity) + DELIMITER
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

        if FORWARD == 1:
            try:
                dbgprint(repr(addr) + ' - forwarding to ' + FORWARDADDR)
                outdata = {
                    'name' : spindle_name,
                    'ID' : spindle_id,
                    'angle' : angle,
                    'temperature' : temperature,
                    'battery' : battery,
                    'gravity' : gravity,
                    'token' : user_token
                }
                out = json.dumps(outdata)
                dbgprint(repr(addr) + ' - sending: ' + out)
                s = socket(AF_INET, SOCK_STREAM)
                s.connect((FORWARDADDR, FORWARDPORT))
                s.send(out)
                rcv = s.recv(BUFF)
                s.close()
                if rcv[0] == ACK :
                    dbgprint(repr(addr) + ' - received ACK - OK!')
                elif rcv[0] == NAK :
                    dbgprint(repr(addr) + ' - received NAK - Not OK...')
                else:
                    dbgprint(repr(addr) + ' - received: ' + rcv)

            except Exception as e:
                dbgprint(repr(addr) + ' Error while forwarding to ' + FORWARDADDR + ': ' + str(e))


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

