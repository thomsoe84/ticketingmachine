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
import redis
import subprocess
import locale
locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

from printer_driver import PrinterC1
from Route import Route
import os
import config
from gpslistener import GpsListener

from ui_main import Ui_MainWindow
#~ from ui_dialoglogin import Ui_DialogLogin


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

PRINTER_PORT = '/dev/ttyS2'

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

class MainForm(QtGui.QMainWindow):	
	def __init__(self):
		super(MainForm, self).__init__()
		
		self.dblayer.connect("tcp://%s:%s" % (config.server_ip, config.server_port))

		self.initUI()
		
		self.redis = redis.Redis('localhost')
		
		# status bar
		self.lblGpsStatus = QtGui.QLabel('Sat: ')
		self.ui.statusbar.addWidget(self.lblGpsStatus)
		self.lblGpsLonLat = QtGui.QLabel('Lon: Lat: ')
		self.ui.statusbar.addWidget(self.lblGpsLonLat)
		self.lblSpeed = QtGui.QLabel('Speed: ')
		self.ui.statusbar.addWidget(self.lblSpeed)
		self.lblTiketNo = QtGui.QLabel('Jml. tiket: ')
		self.ui.statusbar.addWidget(self.lblTiketNo)
		
		self.route = Route(config.route, config.destinations)
		self.ui.lblBusID.setText(config.bus_plateno)
		
		self.ui.lvDestinations.clicked.connect(self.destinationClicked)
		self.ui.pbPrint.clicked.connect(self.printTicket)
		self.ui.pbSwitchDirection.clicked.connect(self.switchDirection)
		
		
		# graphics box to show track, agents, etc
		self.scene=QtGui.QGraphicsScene()
		self.ui.gvTrack.setScene(self.scene)
		self.scene.setSceneRect(0,0,777,87)
		self.marginLR = 30
		self.linelength = self.scene.width() - (2 * self.marginLR)		
		self.drawTrackBackground()
		
		# placeholder for arrow showing actual vehicle position
		self.arrow = None
		
		#~ self.gpsSocket = QtNetwork.QUdpSocket(self)
		#~ self.gpsSocket.bind(45454)
		#~ self.gpsSocket.readyRead.connect(self.processPendingDatagrams)
		
		# start new thread to listen to gps signal
		self.gpsThread = GpsListener(configusb.gpsport, config.gps_baudrate)
		self.gpsThread.message.connect(self.gpsReceived)
		self.gpsThread.sat_info.connect(self.sat_infoReceived)
		self.gpsThread.speed.connect(self.speedReceived)
		self.gpsThread.start()

		# Timer for sending position every 60 seconds to server
		self.sendGpsTimer = QtCore.QTimer(self)
		self.sendGpsTimer.timeout.connect(self.sendGpsPosition)
		self.sendGpsTimer.start(60000)
		
		# print init messages to printer
		p = PrinterC1(config.printer_port, 9600)
		p.selectFont1(2)
		p.printString('Mesin Tiket Bus')
		p.printString( config.company_name)
		p.printString( 'Bus: %s' % config.bus_plateno)
		p.cutPaper(0)
		p.close()
		
		logger.debug('init finished')
	
	def initUI(self):
		self.ui = Ui_MainWindow()
		self.ui.setupUi(self)
		
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
		#~ logger.debug('type of gpsPos: %s %s' % (type(gpsPos), repr(gpsPos)))
		if gpsPos[QtCore.QString('type')] == 0:
			if gpsPos[QtCore.QString('lon')] and gpsPos[QtCore.QString('lat')]:
				self.updateTrackPosition(gpsPos)
				self.lblGpsLonLat.setText( 'Lon: {0:.6f} Lat: {1:.6f}'.format(gpsPos[QtCore.QString('lon')], gpsPos[QtCore.QString('lat')]))
				self.lblGpsLonLat.lon = gpsPos[QtCore.QString('lon')]
				self.lblGpsLonLat.lat = gpsPos[QtCore.QString('lat')]
				
				curAgent = self.getAgentInCurrentLocation(gpsPos, config.agents)				
				if self.ui.lblAgent.text() != curAgent:
					self.ui.lblAgent.setText(curAgent if curAgent else 'Di luar agen')
					self.updateDestinations()
					
					# reset price, distance
					self.ui.lblPrice.setText('')
					self.ui.lblDistance.setText('')					
			else:
				self.ui.lblAgent.setText('GPS no signal')
				# reset price, distance
				self.ui.lblPrice.setText('')
				self.ui.lblDistance.setText('')	
			
	def speedReceived(self, speed):
		self.lblSpeed.setText('Speed: %s km/jam' % (speed))
		
	def sat_infoReceived(self, sat_info):
		self.lblGpsStatus.setText('Sat: %s' % (sat_info))
	
	def updateDestinations(self):
		imodel = QtGui.QStringListModel()
		new_destinations  = []
		if str(self.ui.lblAgent.text()) in config.agents:
			for dest in self.route.getDestinations():
				if self.route.simpleDistanceTo(config.agents[str(self.ui.lblAgent.text())]['latlon'], normalized = True) < self.route.simpleDistanceTo(self.route.getDestinations()[dest]['latlon'], normalized = True):
					new_destinations.append(dest)

			imodel.setStringList(new_destinations)
			self.ui.lvDestinations.setModel(imodel)
			self.lvSelection = self.ui.lvDestinations.selectionModel()
		else:
			#~ logger.info('agent not in config.agents')
			pass
		
	def getAgentInCurrentLocation(self, gpsPos, agents):
		#~ print curPos, agents
		for agent in agents:
			dist = abs(self.route.distanceTo((gpsPos[QtCore.QString('lon')], gpsPos[QtCore.QString('lat')]), agents[agent]['latlon']))
			#~ print dist		
			if dist <= (agents[agent]['radius'] / 1000.0):
				return agent
		return None
	
	def destinationClicked(self, index):
		dest = str(index.data().toString())
		
		if dest:
			self.ui.lblDestination.setText(dest)
			if str(self.ui.lblAgent.text()) in config.agents:
				distance = self.route.distanceTo(
					config.agents[str(self.ui.lblAgent.text())]['latlon'], 
					self.route.getDestinations()[dest]['latlon']
				)
				price = self.calculatePrice(str(self.ui.lblAgent.text()), dest, distance)
				self.ui.lblPrice.setText('%s %s' % ('Rp. ', locale.format('%d', price, grouping=True)))
				self.ui.lblPrice.price = price
				self.ui.lblDistance.setText('Jarak: {0:.1f} km'.format(distance))
				self.ui.lblDistance.distance = distance
				self.say(dest)
			else:
				self.ui.statusbar.showMessage('Di luar agen', 2000)
				self.say('Di luar agen')
		else:
			self.ui.lblDestination.setText('-')
			self.ui.statusbar.showMessage('Error pemilihan tujuan', 2000)
			
	def say(self, tosay):
		#~ subprocess.call('espeak -vid+f3 "%s"' % tosay, shell=True)
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
		if str(self.ui.lblAgent.text()) in config.agents:
			ind = self.lvSelection.currentIndex()
			if ind.row() >= 0:		# if any destination selected
				dest = str(self.ui.lvDestinations.model().stringList()[ind.row()])
				# print ticket
				#~ try:
				if config.printer_enabled:
					self.say('Cetak tiket %s' % dest)
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
                                        if int(self.redis.get('discountTicketCounter')) >= 3:
						isTicketFree = True
						self.redis.set('discountTicketCounter', 0)
						
					p = PrinterC1(config.printer_port, 9600)
					p.selectFont1(2)

					if isTicketFree:
                                                p.printString( config.company_name)
                                                p.printString(dest, 2, 4)
                                                p.printString(curdt.strftime('%d-%b-%Y %H:%M' ), 2, 4)
                                                p.printString('GRATIS PROMO')
                                                p.selectFont1(0)
                                                p.printString( 'Agen: %s' % str(self.ui.lblAgent.text()))
                                                p.printString(str(self.ui.lblDistance.text()))
                                                p.printString( 'Bus: %s' % config.bus_plateno)
                                                p.printString( 'Tiket#: %s' % self.redis.get(curdt.strftime('%Y%m%d:ticket_no')))
                                                p.printBarcode(2, '%03d%010d' % (config.bus_id, gpsdt))
					else:
                                                p.printString( config.company_name)
                                                p.printString(dest, 2, 4)
                                                p.printString(curdt.strftime('%d-%b-%Y %H:%M' ), 2, 4)
                                                p.printString( str(self.ui.lblPrice.text()), 2, 4)
                                                p.selectFont1(0)
                                                p.printString( 'Agen: %s' % str(self.ui.lblAgent.text()))
                                                p.printString(str(self.ui.lblDistance.text()))
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
					self.redis.set(curdt.strftime('%Y%m%d:setoran'), int(self.redis.get(curdt.strftime('%Y%m%d:setoran'))) + int(self.ui.lblPrice.price))

					self.redis.rpush('mq', '$TIKET%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\r\n' % (
						config.bus_plateno, 
						gpsdt,
						self.redis.get(curdt.strftime('%Y%m%d:ticket_no')),
						self.redis.get(curdt.strftime('%Y%m%d:setoran')),
						str(self.ui.lblAgent.text()),
						dest, 
						self.ui.lblPrice.price if not isTicketFree else '0', 
						'{0:.1f}'.format(self.ui.lblDistance.distance), 
						self.lblGpsLonLat.lon, 
						self.lblGpsLonLat.lat
					))
					self.redis.save()
					
					self.lblTiketNo.setText('Jml. tiket: %s' % self.redis.get(curdt.strftime('%Y%m%d:ticket_no')))
				#~ except Exception as ex:
					#~ logger.error('cannot print ticket %s' % ex )
					#~ self.ui.statusbar.showMessage('Printer error', 2000)
			else:
				self.ui.statusbar.showMessage('Silahkan memilih tujuan', 2000)
		else:
			# show info that cannot print ticket because outside of agent area
			self.ui.statusbar.showMessage('Di luar agen', 2000)
	
	def switchDirection(self):
		logger.info('Switched direction')
		self.route.switchDirection()
		self.updateDestinations()
		self.updateTrackDirection()
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
	app = QtGui.QApplication(sys.argv)
	app.setStyle(QtGui.QStyleFactory.create("plastique"))
	ex = MainForm()
	#~ ex.show()
	ex.showFullScreen()
	sys.exit(app.exec_())

if __name__ == '__main__':
	main() 
