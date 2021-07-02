#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
from PyQt4 import QtGui, QtCore, QtNetwork
import time
from datetime import datetime
import simplejson
import zlib
import sha
import base64
import config
import configusb
import binascii
import uuid
from decimal import Decimal
import zmq
import redis
import subprocess
import locale
locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

from printer_driver import PrinterC1
from Route import Route
import os
import config
from gpslistener import GpsListener
from gpiolistener import GPIOListener
from LCD40X4 import GPIO, lcd_init, lcd_goto, lcd_string, GPIO


import logging
import logging.handlers
logger = logging.getLogger('')
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s %(thread)d %(levelname)-5s %(message)s')
fh = logging.handlers.RotatingFileHandler('log.txt', maxBytes=10000000, backupCount=5)
fh.setFormatter(formatter)
ch = logging.StreamHandler()
ch.setFormatter(formatter)
logger.addHandler(fh)
logger.addHandler(ch)

PRINTER_PORT = '/dev/ttyAMA0'

class SpeechThread(QtCore.QThread):
	update = QtCore.pyqtSignal(str)
	def __init__(self, tosay):
		QtCore.QThread.__init__(self)
		self.tosay = tosay
	def __del__(self):
		self.wait()

	def run(self):
		subprocess.call('espeak -vid+f3 "%s"' % self.tosay, shell=True)
		#~ self.terminate()

class MainApp(QtCore.QObject):	
	def __init__(self):
		QtCore.QObject.__init__(self)
		self.context = zmq.Context()
		self.dblayer = self.context.socket(zmq.REQ)
		self.dblayer.connect("tcp://%s:%s" % (config.server_ip, config.server_port))

		
		self.redis = redis.Redis('localhost')
		
		self.route = Route(config.route, config.destinations)
		
		# start new thread to listen to gps signal
		self.gpsThread = GpsListener(configusb.gpsusbport, config.gps_baudrate)
		self.gpsThread.message.connect(self.gpsReceived)
		self.gpsThread.sat_info.connect(self.sat_infoReceived)
		self.gpsThread.speed.connect(self.speedReceived)
		self.gpsThread.start()

		# start new thread to listen to gpio signal
		dests = []
		for d in config.destinations[0]:
			dests.append(d)

		self.gpioThread = GPIOListener(dests)
		self.gpioThread.destinationPressed.connect(self.destinationChosen)
		self.gpioThread.printPressed.connect(self.printTicket)
		self.gpioThread.directionSwitched.connect(self.switchDirection)
		self.gpioThread.start()

		# Timer for sending position every 60 seconds to server
		self.sendGpsTimer = QtCore.QTimer(self)
		self.sendGpsTimer.timeout.connect(self.sendGpsPosition)
		self.sendGpsTimer.start(60000)

		# current state (Agent, destination, price)
		self.currentAgent = None
		self.currentDestination = None
		self.currentDistance = None
		self.currentLon = None
		self.currentLat = None
		
		# print init messages to printer
		p = PrinterC1(config.printer_port, 9600)
		p.selectFont1(2)
		p.printString('Mesin Tiket Bus')
		p.printString( config.company_name)
		p.printString( 'Bus: %s' % config.bus_plateno)
		p.cutPaper(0)
		p.close()

		# init LCD
		#GPIO.setmode(GPIO.BCM)       # Use BCM GPIO numbers
		#GPIO.setup(LCD_E, GPIO.OUT)  # E
		#GPIO.setup(LCD_E2, GPIO.OUT)  # E2
		#GPIO.setup(LCD_RS, GPIO.OUT) # RS
		#GPIO.setup(LCD_D4, GPIO.OUT) # DB4
		#GPIO.setup(LCD_D5, GPIO.OUT) # DB5
		#GPIO.setup(LCD_D6, GPIO.OUT) # DB6
		#GPIO.setup(LCD_D7, GPIO.OUT) # DB7
		#GPIO.setup(LED_ON, GPIO.OUT) # Backlight enable

	
		# Initialise display
		lcd_init()
		lcd_string('Inisiasi sistem selesai..', 1, 1)
		
		self.updateRouteDisplay()	
		logger.debug('init finished')
		self.say('Mesin tiket siap digunakan')
	
	def sendGpsPosition(self):
		#~ logger.debug(self.gpsThread.lastpos)
		try:
			if self.gpsThread.lastpos:
				# ITPRO861001000786141,11025.595867,-659.625256,31,20121008035615.000,15,0,13,1,
				gprmclon = 100 *(int(self.gpsThread.lastpos['lon']) + ((self.gpsThread.lastpos['lon'] - int(self.gpsThread.lastpos['lon'])) / 100 * 60))
				gprmclat = 100 *(int(self.gpsThread.lastpos['lat']) + ((self.gpsThread.lastpos['lat'] - int(self.gpsThread.lastpos['lat'])) / 100 * 60))
				gpsmsg = 'ITPRO%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,\r\n' % (
					config.bus_plateno, 
					gprmclon, 
					gprmclat,
					self.gpsThread.lastpos['alt'], 
					time.strftime("%Y%m%d%H%M%S", time.gmtime(self.gpsThread.lastpos['gpsdt'])), 
					self.gpsThread.lastpos['no_sat'], 
					self.gpsThread.lastpos['speed'], 
					self.gpsThread.lastpos['bearing'],
					'A',
					self.gpsThread.lastpos['ext_power'],
					'',
				)
				logger.debug('SENDGPSINFO: %s' % gpsmsg)
				self.redis.rpush('mq', gpsmsg)
			else:
				logger.info('SENDGPSINFO: GPS not set, not sending position to server..')
		except Exception:
			e = sys.exc_info()
			logger.error('SENDGPSINFO: Error sending GPS info: %s %s' % (e[0], e[1]))
		
	def gpsReceived(self, gpsPos):
		#~ print newpos
		logger.debug('type of gpsPos: %s %s' % (type(gpsPos), repr(gpsPos)))
		if gpsPos['type'] == 0:
			if gpsPos['lon'] and gpsPos['lat']:
				#self.updateTrackPosition(gpsPos)
				#lcd_goto( 'Lon: {0:.6f} Lat: {1:.6f}'.format(gpsPos['lon'], gpsPos['lat']), 0, 3)
				self.currentLon = gpsPos['lon']
				self.currentLat = gpsPos['lat']
				
				curAgent = self.getAgentInCurrentLocation(gpsPos, config.agents)				
				if self.currentAgent != curAgent:
					self.updateCurrentAgent(curAgent)
					#self.updateDestinations()
					
					if not curAgent:
						self.updateCurrentAgent('Di luar area')
						# reset price, distance
						self.updateDestinationPriceDistance('---', '---', '---')
					self.currentAgent = curAgent
			else:
				self.updateCurrentAgent('Belum mendapat sinyal GPS..')
				# reset price, distance
				self.updateDestinationPriceDistance('---', '---', '---')

	def updateCurrentAgent(self, newAgent):
		logger.debug('updateCurrentagent: %s' % newAgent)
		lcd_string('Agen: %s' % newAgent, 1, 1)

	def updateDestinationPriceDistance(self, dest, price, distance):
		if dest != '---':
			lcd_string("Tujuan: {0}  Harga: Rp {1:,}".format(dest, price), 1, 2)
			self.currentDestination = dest
			self.currentPrice = price
			self.currentDistance = distance
		else:
			lcd_string("Tujuan: ---  Harga: ---", 1, 2)
			self.currentDestination = None
			self.currentPrice = None
			self.currentDistance = None

	def updateStatus(self, status, showTime):
		lcd_string('{0}'.format(status), 1, 3)
		self.say(status)
		QtCore.QTimer.singleShot(showTime, self.resetStatus)

	def resetStatus(self):
		lcd_string('', 1, 3)
			
	def speedReceived(self, speed):
		lcd_goto(('%s kmh' % speed).ljust(7),0,4)
		
	def sat_infoReceived(self, sat_info):
		lcd_goto(('Sat:%s' % sat_info).ljust(6),8,4)

	def updateNoTicket(self, ticket_no):
		lcd_goto(('Tkt:%s' % ticket_no).ljust(7),15,4)

	def updateRouteDisplay(self):
		dests = self.route.getDestinationNames()
		lcd_goto(('%s->%s' % (dests[0], dests[-1])).ljust(17),23,4)

	def getAgentInCurrentLocation(self, gpsPos, agents):
		#~ print curPos, agents
		for agent in agents:
			dist = abs(self.route.distanceTo((gpsPos['lon'], gpsPos['lat']), agents[agent]['latlon']))
			#~ print dist		
			if dist <= (agents[agent]['radius'] / 1000.0):
				return agent
		return None
	
	def destinationChosen(self, dest_qstring):
		dest = str(dest_qstring)
		if dest:
			
			if self.currentAgent:
				# check if selected destination is valid
				if self.route.simpleDistanceTo(config.agents[self.currentAgent]['latlon'], normalized = True) < self.route.simpleDistanceTo(self.route.getDestinations()[dest]['latlon'], normalized = True):
					distance = self.route.distanceTo(
						config.agents[self.currentAgent]['latlon'], 
						self.route.getDestinations()[dest]['latlon']
					)
					price = self.calculatePrice(self.currentAgent, dest, distance)
					self.updateDestinationPriceDistance(dest, price, distance)
					self.say(dest)
				else:
					self.updateDestinationPriceDistance('---', '---', '---')
					self.updateStatus('Tujuan tidak valid', 2000)

			else:
				self.updateStatus('Di luar agen', 2000)
				self.updateDestinationPriceDistance('---', '---', '---')
		else:
			self.updateDestinationPriceDistance('---', '---', '---')
			self.updateStatus('Error pemilihan tujuan', 2000)
			
	def say(self, tosay):
		subprocess.call('espeak -vid+f3 "%s" 2>/dev/null &' % tosay, shell=True)
		#~ speechThread = SpeechThread(tosay)
		#~ speechThread.start()
		pass
		
	def calculatePrice(self, fromAgent, destination, distance):
		print (fromAgent, destination, distance)
		for prices in self.route.getDestinations()[destination]['pricelist']:
			if fromAgent in prices['from']:
				return prices['price']
		#~ return max(config.minimal_price, math.ceil((distance*config.price_per_km)/1000.0) * 1000)
		return 0
		
	def printTicket(self):
		if self.currentAgent in config.agents:
			if self.currentDestination:		# if any destination selected
				dest = self.currentDestination
				# print ticket
				#~ try:
				if config.printer_enabled:
					self.say('Mencetak tiket ke %s' % dest)
					gpsdt = self.gpsThread.lastpos['gpsdt']
					curdt = datetime.fromtimestamp(gpsdt)
					
					# initialize or increment global ticket counter
					if not self.redis.get('discountTicketCounter'):
						self.redis.set('discountTicketCounter', 0)
					self.redis.incr('discountTicketCounter')
					
					# initialize or increment daily ticket counter
					if not self.redis.get(curdt.strftime('%Y%m%d:ticket_no')):
						self.redis.set(curdt.strftime('%Y%m%d:ticket_no'), 0)
					self.redis.incr(curdt.strftime('%Y%m%d:ticket_no'))					
					
					isTicketFree = False
					if int(self.redis.get('discountTicketCounter')) >= 100:
						isTicketFree = True
						self.redis.set('discountTicketCounter', 0)
						
					p = PrinterC1(config.printer_port, 9600)
					p.selectFont1(2)
					
					if isTicketFree:
						p.printString(config.company_name)
						p.printString(dest, 2, 4)
						p.printString(curdt.strftime('%d-%b-%Y %H:%M' ), 2, 4)
						p.printString('GRATIS PROMO') 
						p.selectFont1(0)
						p.printString( 'Agen: %s' % self.currentAgent)
						p.printString('{0:.1f} km'.format(self.currentDistance))
						p.printString( 'Bus: %s' % config.bus_plateno)
						p.printString( 'Tiket#: %s' % self.redis.get(curdt.strftime('%Y%m%d:ticket_no')))
						p.printBarcode(2, '%03d%010d' % (config.bus_id, gpsdt))
					else:	
						p.printString(config.company_name)
						p.printString(dest, 2, 4)
						p.printString(curdt.strftime('%d-%b-%Y %H:%M' ), 2, 4)
						p.printString('Rp {0:,}'.format(self.currentPrice), 2, 4)
						p.selectFont1(0)
						p.printString( 'Agen: %s' % self.currentAgent)
						p.printString('{0:.1f} km'.format(self.currentDistance))
						p.printString( 'Bus: %s' % config.bus_plateno)
						p.printString( 'Tiket#: %s' % self.redis.get(curdt.strftime('%Y%m%d:ticket_no')))
						p.printBarcode(2, '%03d%010d' % (config.bus_id, gpsdt))
					p.cutPaper(0)
					p.close()
					#~ print 'PO. Sumber Alam'
					#~ print config.bus_plateno
					#~ print curdt.strftime('%d-%b-%Y %H:%M', time.localtime(curtime))
					#~ print 'Tujuan: {}'.format(destListBox.selectedItem)
					#~ print 'Jarak: 0{:.1f} km'.format(distance)
					#~ print 'Harga: Rp. {0:.0f}'.format(self.ui.lblPrice.text())
					#~ print '%03d%010d' % (config.bus_id, int(curtime))
					
					# initialize or add daily total setoran
					if not self.redis.get(curdt.strftime('%Y%m%d:setoran')):
						self.redis.set(curdt.strftime('%Y%m%d:setoran'), 0)
					self.redis.set(curdt.strftime('%Y%m%d:setoran'), int(self.redis.get(curdt.strftime('%Y%m%d:setoran'))) + self.currentPrice)

					self.redis.rpush('mq', '$TIKET%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\r\n' % (
						config.bus_plateno, 
						gpsdt,
						self.redis.get(curdt.strftime('%Y%m%d:ticket_no')),
						self.redis.get(curdt.strftime('%Y%m%d:setoran')),
						self.currentAgent,
						dest, 
						self.currentPrice if not isTicketFree else '0', 
						'{0:.1f}'.format(self.currentDistance), 
						self.currentLon, 
						self.currentLat
					))
					
					self.updateNoTicket(self.redis.get(curdt.strftime('%Y%m%d:ticket_no')))
					
					try:
						self.redis.save()
					except Exception:
						e = sys.exc_info()
						logger.warning('Error redis.save(), maybe redis is saving, it is OK: %s %s' % (e[0], e[1]))

					
				#~ except Exception as ex:
					#~ logger.error('cannot print ticket %s' % ex )
					#~ self.ui.statusbar.showMessage('Printer error', 2000)
			else:
				self.updateStatus('Tujuan belum dipilih', 2000)
		else:
			# show info that cannot print ticket because outside of agent area
			self.updateStatus('Di luar agen', 2000)
	
	def switchDirection(self, direction):
		logger.info('Switched direction')
		self.updateDestinationPriceDistance('---', '---', '---')
		self.route.switchDirection()
		self.updateRouteDisplay()
		self.say('Ganti arah')
		
	def drawTrackBackground(self):	
		linePosY = self.scene.height() / 2
		
		# draw horizontal line
		self.scene.addLine(self.marginLR, linePosY, self.marginLR + self.linelength, linePosY)
		
		alternateUpDown = True
		prevUpRightX = 0
		prevDownRightX = 0
		wasDownDown = False
		wasUpUp = False
		
		# draw agency fonts
		for dest in config.agents:
			destItem = self.scene.addSimpleText(dest)
			distanceDestFactor = self.route.simpleDistanceTo(config.agents[dest]['latlon'], normalized = True)
			posLineX = self.marginLR + (distanceDestFactor * self.linelength)
			posTextX = posLineX
			if (posTextX - int(destItem.boundingRect().width() / 2)) < 0:
				# first text
				posTextX = 0
			elif (posTextX + int(destItem.boundingRect().width() / 2)) > self.scene.width():
				posTextX = self.size[0] - destItem.boundingRect().width() 
			else:
				posTextX = posTextX - int(destItem.boundingRect().width()  / 2)
			posTextY = 0
			if alternateUpDown:
				# text below line
				if wasDownDown or ((posTextX - self.marginLR) >= prevDownRightX):
					posTextY = linePosY + 10
					wasDownDown = False
				else:
					posTextY = linePosY + 10 + destItem.boundingRect().height()
					wasDownDown = True
			else:
				# text above line
				if wasUpUp or ((posTextX - self.marginLR) >= prevUpRightX):
					posTextY= linePosY - (6 + destItem.boundingRect().height())
					wasUpUp = False
				else:
					posTextY= linePosY - (6 + (2 *destItem.boundingRect().height()))
					wasUpUp = True

			destItem.setPos(posTextX, posTextY)
			
			# draw connecting line between horizontal to font
			self.scene.addLine(
				posLineX, linePosY, 
				posLineX, posTextY if alternateUpDown else posTextY + destItem.boundingRect().height() - 4
			)
			
			if alternateUpDown:
				prevDownRightX = posTextX - self.marginLR + destItem.boundingRect().width()
			else:
				prevUpRightX = posTextX - self.marginLR + destItem.boundingRect().width()			

			alternateUpDown = not alternateUpDown
		
	def updateTrackDirection(self):
		if self.arrow:
			shape = [ (-10, - 8 ), (10,  0), (-10,  8 ), (0,  0) ] if self.route.mode == '>' else [ (10, - 8 ), (-10,  0), (10,  8 ), (0,  0) ]
			pol = QtGui.QPolygonF()
			for point in shape: 
				pol.append(QtCore.QPointF(point[0], point[1]))
			self.arrow.setPolygon(pol)
		else:
			self.ui.statusbar.showMessage('Menunggu sinyal GPS...', 2000)
	
	def updateTrackPosition(self, gpsPos):
		# draw arrow showing actual bus position
		if not self.arrow:			
			self.arrow = QtGui.QGraphicsPolygonItem()
			self.arrow.setBrush(QtCore.Qt.red)
			self.arrow.setPen(QtCore.Qt.red)
			self.arrow.setVisible(False)		
			self.scene.addItem(self.arrow)				
			self.arrow.direction = None
			
		if not self.arrow.direction or (self.arrow.direction != self.route.mode):
			self.updateTrackDirection()
			self.arrow.direction = self.route.mode
			
			
		progress = self.route.simpleDistanceTo((gpsPos[QtCore.QString('lon')], gpsPos[QtCore.QString('lat')]), normalized = True)
		
		if self.route.mode == '<':
			progress = 1.0 - progress
		self.arrow.setPos(self.marginLR+int(self.linelength*progress), self.scene.height() / 2)
		self.arrow.setVisible(True)

def main():	
	app = QtCore.QCoreApplication(sys.argv)
	#app.setStyle(QtGui.QStyleFactory.create("plastique"))
	ex = MainApp()
	#~ ex.show()
	#ex.showFullScreen()
	sys.exit(app.exec_())

if __name__ == '__main__':
	main() 
