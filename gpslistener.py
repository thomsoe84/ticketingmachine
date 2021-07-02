from PyQt4 import QtCore, QtNetwork
import calendar
import time
import datetime
import serial
import re
from decimal import Decimal
import sys
import math

import logging
logger = logging.getLogger('root')

class GpsListener(QtCore.QThread):
	message = QtCore.pyqtSignal(dict)
	speed = QtCore.pyqtSignal(str)
	sat_info = QtCore.pyqtSignal(str)
	
	
	def __init__(self, port, baudrate):
		QtCore.QThread.__init__(self)
		logger.info("Listening to gps serial updates..")
		self.gpsdevice = serial.Serial(port=port, baudrate=baudrate, timeout=5)
		self.running = True
		self.lastpos = {'bearing': 0, 'gpsdt': 0, 'lon': 0.0, 'lat': 0.0, 'speed': 0, 'alt': 0, 'type': 0, 'no_sat': 0, 'ext_power': 1}
		self.prevgpsdt = 0
		self.newdata = ""
		self.line = ""

	def readBuffer(self):
		try:
			#data = self.gpsdevice.read(1)
			#n = self.gpsdevice.inWaiting()
			#logger.debug('got %s byte' % n)
			#if n:
			#	data = data + self.gpsdevice.read(n)
			#return data

			data = self.gpsdevice.readline()
			logger.debug(data)

		except Exception, e:
			print "Big time read error, what happened: ", e
			sys.exit(1)
			
	def __del__(self):
		self.wait()
	
	def run(self):
		while self.running:
			# If we have new data from the data CRLF split, then 
			# it's the start + data of our next NMEA sentence.  
			# Have it be the start of the new self.line
			if self.newdata: 
				self.line = self.newdata
				self.newdata = ""

			# Read from the input buffer and append it to our self.line 
			# being constructed
			#self.line = self.line + self.readBuffer()
			# Look for  \x0d\x0a or \r\n at the end of the self.line (CRLF) 
			# after each input buffer read so we can find the end of our 
			# self.line being constructed

			data = self.gpsdevice.readline()
			if data:
			#if re.search("\r\n", self.line):
				# Since we found a CRLF, split it out
				#~ logger.debug(self.line)
				#data, self.newdata = self.line.split("\r\n", 1)

				#~ print "----" + str(datetime.datetime.now()) + "----"
				#~ print data
				#~ print
				
				if data.startswith('$GPRMC'):
					tdata = data.split(',')
					#~ 0 $GPRMC
					#~ 1 045121.000	# time
					#~ 2 A			# gps status A:valid, V: warning
					#~ 3 0659.6148	# latitude
					#~ 4 S			# latitude direction
					#~ 5 11025.5982	# longitude
					#~ 6 E			# longitude direction
					#~ 7 0.17		# speed in knots
					#~ 8 230.95		# course
					#~ 9 140813		# date
					#~ 10 
					#~ 11 
					#~ 12 A*74
					if tdata[2] == 'A':						
						#~ logger.debug(tdata)
						(dlonf, dloni) = math.modf(Decimal(tdata[5]) / 100)
						lon = dloni + round(dlonf * 100 / 60, 6)
						if tdata[6] == 'W':
							lon = -lon
						self.lastpos['lon'] = lon
						
						(dlatf, dlati) = math.modf(Decimal(tdata[3]) / 100)
						lat = dlati + round(dlatf * 100 / 60, 6)
						if tdata[4] == 'S':
							lat = -lat
						self.lastpos['lat'] = lat
						
						self.lastpos['bearing'] = int(Decimal(tdata[8]).to_integral_value())
						self.lastpos['gpsdt'] = calendar.timegm(time.strptime(tdata[9]+tdata[1], '%d%m%y%H%M%S.%f'))
				
				if data.startswith('$GPGGA'):
					tdata = data.split(',')
					#~ 0 $GPGGA
					#~ 1 080134.000	# time
					#~ 2 0659.6118	# latitude
					#~ 3 S			# lat dir
					#~ 4 11025.5999	# lon
					#~ 5 E			# lon dir
					#~ 6 1			# fix quality 0:invalid, 1:gps fix, 2:dgps fix
					#~ 7 10			# sat#
					#~ 8 0.95		# HDOP
					#~ 9 32.6		# alt
					#~ 10 M			
					#~ 11 7.3
					#~ 12 M
					#~ 13 
					#~ 14 *7E
					if tdata[6] != '0':
						#~ logger.debug(tdata)
						(dlonf, dloni) = math.modf(Decimal(tdata[4]) / 100)
						lon = dloni + round(dlonf * 100 / 60, 6)
						if tdata[5] == 'W':
							lon = -lon
						self.lastpos['lon'] = lon
						
						(dlatf, dlati) = math.modf(Decimal(tdata[2]) / 100)
						lat = dlati + round(dlatf * 100 / 60, 6)
						if tdata[3] == 'S':
							lat = -lat
						self.lastpos['lat'] = lat
						
						self.lastpos['alt'] = int(Decimal(tdata[9]).to_integral_value())					
						self.lastpos['no_sat'] = int(tdata[7])
					
				if data.startswith('$GPVTG'):
					tdata = data.split(',')
					#~ 0 $GPVTG
					#~ 1 236.71
					#~ 2 T
					#~ 3 
					#~ 4 M
					#~ 5 0.74
					#~ 6 N
					#~ 7 1.37
					#~ 8 K
					#~ 9 A*3A
					#~ logger.debug(tdata)
					self.lastpos['speed'] = int(Decimal(tdata[7]).to_integral_value())
					self.speed.emit(str(self.lastpos['speed']))
					
				#~ print self.lastpos
				if self.lastpos['gpsdt'] - self.prevgpsdt > 5:                                  
					# logger.debug(self.lastpos)
					self.message.emit(self.lastpos)
					
					# emit sat info 
					self.sat_info.emit('%s' % self.lastpos['no_sat'])

					#~ print self.lastpos['gpsdt'], self.prevgpsdt, self.lastpos['gpsdt'] - self.prevgpsdt

					self.prevgpsdt = self.lastpos['gpsdt']


				# Reset our self.line constructer variable
				self.line = ""

def gpsReceived(str):
	logger.debug(str)
	
def speedReceived(str):
	logger.debug('speed: %s' % str)
				
if __name__ == '__main__':
	import logging.handlers
	logger.setLevel(logging.DEBUG)
	formatter = logging.Formatter('%(asctime)s %(thread)d %(levelname)-5s %(message)s')
	fh = logging.handlers.RotatingFileHandler('log.txt', maxBytes=10000000, backupCount=5)
	fh.setFormatter(formatter)
	ch = logging.StreamHandler()
	ch.setFormatter(formatter)
	logger.addHandler(fh)
	logger.addHandler(ch)
	# start new thread to listen to gps signal
	gpsListener = GpsListener('/dev/ttyUSB0', 9600)
	gpsListener.message.connect(gpsReceived)
	gpsListener.speed.connect(speedReceived)
	gpsListener.sat_info.connect(speedReceived)
	#~ QtCore.QTimer.singleShot(0, gpsThread.start)
	gpsListener.start()
	
	app = QtCore.QCoreApplication(sys.argv)
	sys.exit(app.exec_())
