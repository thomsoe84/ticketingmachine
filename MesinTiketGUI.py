import math
import pygame
from pygame.locals import *
from pygame.color import THECOLORS
from ListBox import ListBox
from TrackBox import TrackBox
from Route import Route
import zmq
import gevent
import os
import config
from printer_driver import PrinterC1
import time
import redis

import logging
import logging.handlers

r = redis.Redis('localhost')

logger = logging.getLogger('')
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s %(levelname)-5s %(message)s')
fh = logging.handlers.RotatingFileHandler('logMesinTiketGUI.txt', maxBytes=10000000, backupCount=5)
fh.setFormatter(formatter)
ch = logging.StreamHandler()
ch.setFormatter(formatter)
logger.addHandler(fh)
logger.addHandler(ch)

context = zmq.Context()
gps_socket = context.socket(zmq.SUB)
gps_socket.connect("tcp://%s:%s" % (config.gpsgprs_gpio_ip, config.gpsgprs_pubport))
gps_socket.setsockopt(zmq.SUBSCRIBE, '')

sendmsg_socket = context.socket(zmq.PUSH)
sendmsg_socket.connect("tcp://%s:%s" % (config.gpsgprs_gpio_ip, config.gpsgprs_pullport))

gpio_socket = context.socket(zmq.SUB)
gpio_socket.connect('tcp://%s:%s' % (config.gpsgprs_gpio_ip, config.gpio_pubport))
gpio_socket.setsockopt(zmq.SUBSCRIBE, '')

route = Route(config.route, config.destinations)

pygame.display.init()
WINSIZE = (pygame.display.Info().current_w,  pygame.display.Info().current_h)
screen = pygame.display.set_mode(WINSIZE)
#~ screen = pygame.display.set_mode(WINSIZE, pygame.FULLSCREEN)
#~ screen.fill(THECOLORS['blue'])
print pygame.display.get_driver()
print WINSIZE
pygame.font.init()
pygame.init()
pygame.mouse.set_visible(False)
pygame.display.set_caption('GPS Bus Ticketing Machine')
clock = pygame.time.Clock()

destListBox = ListBox(screen, route.getDestinationNames(), 8, 0, 185)

currentGPS = None

trackBox = TrackBox(screen, route, config.agents, (WINSIZE[0], 80), 0, 5)

def updateTrack():
	trackBox.updatePosition(currentGPS)

priceSurface = pygame.Surface((int(WINSIZE[0]/2), WINSIZE[1] - 80))
priceFont = pygame.font.Font(None, 136)
distanceFont = pygame.font.Font(None, 40) 

gpsSurface = pygame.Surface((int(WINSIZE[0]/2), 24))
gpsFont = pygame.font.Font(None, 24)

titleFont = pygame.font.Font(None, 72)

def calculatePrice(fromAgent, destination, distance):
	print (fromAgent, destination, distance)
	for prices in route.getDestinations()[destination]['pricelist']:
		if fromAgent in prices['from']:
			return prices['price']
	#~ return max(config.minimal_price, math.ceil((distance*config.price_per_km)/1000.0) * 1000)
	return 0
	
def updatePrice(price, distance, destination, agent):	
	priceSurface.fill(THECOLORS['black'])
	
	textTitleSurface = titleFont.render(
		'PO. Sumber Alam', 
		True, 
		THECOLORS['red'],
		THECOLORS['black'], 	# background color
	)
	textAgentSurface = titleFont.render(
		'Agen: %s' % agent, 
		True, 
		THECOLORS['yellow'],
		THECOLORS['black'], 	# background color
	)
	textDestSurface = titleFont.render(
		destination if destination else '-', 
		True, 
		THECOLORS['yellow'],
		THECOLORS['black'], 	# background color
	)
	textPriceSurface = priceFont.render(
		'Rp. {:,.0f}'.format(price), 
		True, 
		THECOLORS['green'],
		THECOLORS['black'], 	# background color
	)
	textDistanceSurface = distanceFont.render(
		'Jarak: {:,.1f} km'.format(distance), 
		True, 
		THECOLORS['gray'],
		THECOLORS['black'], 	# background color
	)
	textBusName = distanceFont.render(
		'Bus: %s' % config.bus_plateno, 
		True, 
		THECOLORS['gray'],
		THECOLORS['black'], 	# background color
	)
	
	priceSurface.blit(textTitleSurface, (0, 0))
	priceSurface.blit(textAgentSurface, (0, 70))
	priceSurface.blit(textDestSurface, (0, 140))
	priceSurface.blit(textPriceSurface, (0, 210))
	priceSurface.blit(textDistanceSurface, (0, 340))
	priceSurface.blit(textBusName, (0, 380))
		
	screen.blit(priceSurface, (int(WINSIZE[0]/2), 110))
	pygame.display.update()
	print 'display updated'
	
def updateGPSstatus(newpos):	
	gpsSurface.fill(THECOLORS['black'])
	

	#~ print distance*280
	textGPSSatnoSurface = gpsFont.render(
		'GPS Satellites: %s %s' % (newpos['no_sat'], newpos['status']), 
		True, 
		THECOLORS['green'],
		THECOLORS['black'], 	# background color
	)

	gpsSurface.blit(textGPSSatnoSurface, (0, 0))
		
	screen.blit(gpsSurface, (int(WINSIZE[0]*.8), int(WINSIZE[1] - 24)))
	pygame.display.update()

def GetAgentInCurrentLocation(curPos, agents):
	#~ print curPos, agents
	for agent in agents:
		dist = abs(route.distanceTo((curPos['lon'], curPos['lat']), agents[agent]['latlon']))
		#~ print dist		
		if dist <= (agents[agent]['radius'] / 1000.0):
			return agent
	return None
	
def buttonDestinationPressed(buttonNo):
	if buttonNo in [0,1,2,3,4,5,6,7]:
		# DESTINATION BUTTON
		if currentGPS:
			curAgent = GetAgentInCurrentLocation(currentGPS, config.agents)
			if curAgent:
				destListBox.selectRow(buttonNo)
				if destListBox.selectedItem:
					distance = route.distanceTo((currentGPS['lon'], currentGPS['lat']), route.getDestinations()[destListBox.selectedItem]['latlon'])
					price = calculatePrice(curAgent, destListBox.selectedItem, distance)
					updatePrice(price, distance, destListBox.selectedItem, curAgent)
				else:
					updatePrice(0.0, 0.0, '---', curAgent)
			else:
				updatePrice(0.0,0.0, destListBox.selectedItem, 'Di luar area agen')
		else:
			updatePrice(0.0, 0.0, destListBox.selectedItem, 'GPS belum aktif')
	elif buttonNo == 8:
		# PRINT BUTTON
		if currentGPS:
			curAgent = GetAgentInCurrentLocation(currentGPS, config.agents)
			if curAgent:
				if destListBox.selectedItem:
					distance = route.distanceTo((currentGPS['lon'], currentGPS['lat']), route.getDestinations()[destListBox.selectedItem]['latlon'])
					price = calculatePrice(curAgent, destListBox.selectedItem, distance)
					updatePrice(price, distance, destListBox.selectedItem, curAgent)
					# print ticket
					try:
						if config.printer_enabled:
							if not r.get(time.strftime('%Y%m%d:ticket_no')):
								r.set(time.strftime('%Y%m%d:ticket_no'), 0)
							r.incr(time.strftime('%Y%m%d:ticket_no'))
							
							p = PrinterC1(config.printer_port, 9600)
							curtime = time.time()
							p.selectFont1(2)
							p.printString( 'PO. Sumber Alam')
							p.printString(destListBox.selectedItem, 2, 4)
							p.printString( time.strftime('%d-%b-%Y %H:%M', time.localtime(curtime)), 2, 4)
							p.printString( 'Rp. {:,.0f}'.format(price), 2, 4)
							p.selectFont1(0)
							p.printString( 'Agen: %s' % curAgent)
							p.printString( 'Jarak: {:,.1f} km'.format(distance))
							p.printString( 'Bus: %s' % config.bus_plateno)
							p.printString( 'Tiket#: %s' % r.get(time.strftime('%Y%m%d:ticket_no')))
							p.printBarcode(2, '%03d%010d' % (config.bus_id, int(curtime)))
							p.cutPaper(0)
							p.close()
							#~ print 'PO. Sumber Alam'
							#~ print config.bus_plateno
							#~ print time.strftime('%d-%b-%Y %H:%M', time.localtime(curtime))
							#~ print 'Tujuan: {}'.format(destListBox.selectedItem)
							#~ print 'Jarak: {:,.1f} km'.format(distance)
							#~ print 'Harga: Rp. {:,.0f}'.format(price)
							#~ print '%03d%010d' % (config.bus_id, int(curtime))
							
							if not r.get(time.strftime('%Y%m%d:setoran')):
								r.set(time.strftime('%Y%m%d:setoran'), 0)
							r.set(time.strftime('%Y%m%d:setoran'), int(r.get(time.strftime('%Y%m%d:setoran'))) + int(price))

							r.rpush('mq', '$TIKET%s,%s,%s,%s,%s,%s,%s,%s,%s\r\n' % (
								config.bus_plateno, 
								r.get(time.strftime('%Y%m%d:ticket_no')),
								r.get(time.strftime('%Y%m%d:setoran')),
								curAgent,
								destListBox.selectedItem, 
								price, 
								'{:,.1f}'.format(distance), 
								currentGPS['lon'], 
								currentGPS['lat']
							))
							r.save()

							
							#sendmsg_socket.send('$TIKET%s,%s,%s,%s,%s,%s' % (config.bus_plateno, destListBox.selectedItem, price, distance, currentGPS['lon'], currentGPS['lat']))
					except Exception as ex:
						logger.error('cannot print ticket %s' % ex )
						updatePrice(0.0, 0.0, 'Printer Error', curAgent)
				else:
					updatePrice(0.0, 0.0, '---', curAgent)
			else:
				updatePrice(0.0,0.0, destListBox.selectedItem, 'Di luar area agen')
		else:
			updatePrice(0.0, 0.0, destListBox.selectedItem, 'GPS belum aktif')
	elif buttonNo in [-1,-2]:
		route.switchDirection()
		updateDestinationListbox()
		trackBox.drawBackground()
		
def updateDestinationListbox():
	new_destinations = []
	for dest in route.getDestinations():
		if currentGPS:
			if route.simpleDistanceTo((currentGPS['lon'], currentGPS['lat']), normalized = True) < route.simpleDistanceTo(route.getDestinations()[dest]['latlon'], normalized = True):
				new_destinations.append(dest)
		else:
			new_destinations.append(dest)
	if new_destinations != destListBox.getItems():
		destListBox.setItems(new_destinations)
		updatePrice(0.0, 0.0, destListBox.selectedItem, '')

def newGPSReceived(newpos):
	global currentGPS
	if newpos['type'] == 0:
		if newpos['lon'] and newpos['lat']:
			currentGPS = newpos
			
			updateTrack()
			print 'newGPSreceived'
			updateDestinationListbox()
			print 'got here 1'
			curAgent = GetAgentInCurrentLocation(currentGPS, config.agents)
			print curAgent
			if curAgent:
				updatePrice(0.0, 0.0, destListBox.selectedItem, curAgent)
			else:
				updatePrice(0.0, 0.0, destListBox.selectedItem, 'Di luar area agen')
			print 'got here'
		else:
			currentGPS = None
			updatePrice(0.0, 0.0, destListBox.selectedItem, 'GPS belum aktif')
	elif newpos['type'] == 1:
		# GPS satelite number information
		updateGPSstatus(newpos)

quitting = False
def pygame_eventloop():
	global quitting
	done = False
	while not done:
		gevent.sleep(0)
		clock.tick(20)
		events = pygame.event.get()
		for e in events:
			if( e.type == QUIT ):
				done = True
				break
				print "Exiting!"
			elif (e.type == KEYDOWN):
				if (e.key == K_0):
					buttonDestinationPressed(0)
				if (e.key == K_1):
					buttonDestinationPressed(1)
				if (e.key == K_2):
					buttonDestinationPressed(2)
				if (e.key == K_3):
					buttonDestinationPressed(3)
				if (e.key == K_4):
					buttonDestinationPressed(4)
				if (e.key == K_5):
					buttonDestinationPressed(5)
				if (e.key == K_6):
					buttonDestinationPressed(6)
				if (e.key == K_7):
					buttonDestinationPressed(7)
				if (e.key == K_p):
					buttonDestinationPressed(8)
				if (e.key == K_s):
					route.switchDirection()
					updateDestinationListbox()
					trackBox.drawBackground()
				if (e.key == K_q):
					quitting = True
					done = True
					# kill gps_listener greenlet
					greenlets[1].kill()
					greenlets[2].kill()
					break

	quitting = True	

def gps_listener():
	global quitting
	try:
		while True:
			newpos = gps_socket.recv_pyobj()
			print type(newpos), repr(newpos)
			newGPSReceived(newpos)
			
			#~ print currentGPS
			if quitting:
				break
		gps_socket.close()
	except:
		print "quitting"

def gpio_listener():
	global quitting
	try:
		while True:
			buttonpressed = gpio_socket.recv_pyobj()
			buttonDestinationPressed(buttonpressed)
			if quitting:
				break
		gpio_socket.close()
	except:
		print 'quitting'

greenlets = [
	gevent.spawn(pygame_eventloop),
	gevent.spawn(gps_listener),
	gevent.spawn(gpio_listener),
]
gevent.joinall(greenlets)


	
	


