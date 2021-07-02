import serial
import os
import math
import time
import datetime
import calendar
import gevent
import gevent.monkey
from gevent.event import AsyncResult, Event
import zmq.green as zmq
from gevent.coros import BoundedSemaphore
from decimal import Decimal
import config
import sys
import logging
import subprocess
import logging.handlers
import redis
import configusb
#import RPi.GPIO as GPIO
#from gps import *
#GPIO.setmode(GPIO.BCM)
#GPIO.setup(30, GPIO.OUT)

r = redis.Redis('localhost')

gevent.monkey.patch_all()

logger = logging.getLogger('')
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s %(levelname)-5s %(message)s')
fh = logging.handlers.RotatingFileHandler('logGPSGPRS.txt', maxBytes=10000000, backupCount=5)
fh.setFormatter(formatter)
ch = logging.StreamHandler()
ch.setFormatter(formatter)
logger.addHandler(fh)
logger.addHandler(ch)

ser = serial.Serial(
	port=configusb.gprsport, 
	baudrate=config.gprs_baudrate, 
	bytesize=8, 
	parity=serial.PARITY_NONE, 
	stopbits=serial.STOPBITS_ONE, 
	timeout=.15)
logger.debug('using port: %s at %s' % (ser.name, ser.baudrate))


imei = 'imeiunset'
lastpos = {'bearing': 0, 'gpsdt': 0, 'lon': 0.0, 'lat': 0.0, 'speed': 0, 'alt': 0, 'type': 0, 'no_sat': 0, 'ext_power': 1}
lastsendpos = 0

lock = BoundedSemaphore(1)
def submitAT(cmd, waitFor = 'OK', waitForResponse = True):
	lock.acquire()
	logger.info('SUBMITAT: %s waitForResponse: %s' % (repr(cmd), waitForResponse))
	ser.write(cmd + '\r\n')
	toreturn = None
	if waitForResponse:
		done = False
		innercounter = 0
		outercounter = 0
		while not done:
			global ares
			try:
				result = ares.get(timeout=15.0)
			except gevent.Timeout:
				logger.error('SUBMITAT: time out, resubmit cmd: %s' % cmd)
				ser.write(cmd + '\r\n')
				outercounter += 1
				continue
			finally:
				ares = AsyncResult()
				
			#~ result = ser.readlines()			
			
			result = [res.strip() for res in result]
			#~ logger.debug('SUBMITAT: wait %s, result: %s' % (waitFor, result))
			if waitFor in result:
				done = True
				if cmd in result:
					toreturn = result[result.index(cmd):]
				else:
					toreturn = result
				continue
			elif 'ERROR' in result:				
				logger.info('SUBMITAT: ERROR, resubmit cmd: %s' % cmd)
				gevent.sleep(1)
				ser.write(cmd + '\r\n')
				outercounter += 1
			elif '\xff\xff' in result:
				logger.debug('SIM module is OFF!!!')
				#GPIO.output(30, 1) 
				#time.sleep(5)
				#GPIO.output(30, 0)

			if outercounter > 5:
				logger.error('SUBMITAT: failed!!!')
				#restart
				#logger.error('RESTARTING..')
				#GPIO.output(30, 1)
				#time.sleep(5)
				#GPIO.output(30, 0)
				break
	else:
		pass
		#~ result = ser.readlines()	
		#~ toreturn = [res.strip() for res in result]
		#~ logger.debug('not wait OK, result: %s' % toreturn)
	lock.release()
	logger.debug('SUBMITAT: finished result: %s' % toreturn)
	return toreturn

def initSIM908():
	eventSIM908Ready.clear()
	eventSerialReady.clear()
	
	logger.debug('INITSIM908')

	done = False
	waitcounter = 0
	logger.debug('before while')
	while not done:
		ser.write('AT\r\n')
		logger.debug('after ser.write')
		global ares
		logger.debug('after global ares')
		#~ result = ares.get()
		#~ ares = AsyncResult()
		
		result = ser.readlines()
		logger.debug('after readlines')
		logger.debug('result: %s' % result)
		for res in result:
			if res == 'OK\r\n':
				done = True
		if done:
			break			
			
		logger.info('Waiting for SIM908..')
		ser.write(chr(26))
				
		gevent.sleep(1)
		waitcounter += 1
		#if waitcounter > 5:
			#logger.error("RESTARTING...")
			#GPIO.output(30, 1)
			#time.sleep(5)
			#GPIO.output(30, 0)
	eventSerialReady.set()
	logger.info('INITSIM908: SIM908 ready..')
	resp = submitAT('ATE1')
	#~ logger.info('INITSIM908: waiting for initialization 3 seconds..')
	#~ time.sleep(3)
	logger.info('INITSIM908: read imei...')
	global imei
	imei = getIMEI()
	logger.info(imei)
	submitAT('AT+CREG=2')
	submitAT('AT+QIHEAD=1')
	#~ submitAT('AT+QICLOSE')
	#~ submitAT('AT+QIDEACT', 'DEACT OK')
	submitAT('AT+QIFGCNT=0')
	submitAT('AT+QICSGP=1,"telkomsel","wap","wap123"')
	#~ submitAT('AT+')
	eventSIM908Ready.set()
	logger.info('INITSIM908: done.')
		
def getIMEI():
	resp = submitAT('AT+GSN')
	toreturn = 0
	for res in resp:
		try:
			toreturn = int(res)
			break
		except:
			pass
	
	if not toreturn:
		logger.error('Cannot get IMEI')

	return toreturn

def checkTcpStatus():
	resp = submitAT('AT+QISTATE')
	return resp
	
def openConnection():
	if checkTcpStatus()[-1].strip() in ['STATE: IP STATUS', 'STATE: TCP CLOSED', 'STATE: CONNECT OK']:
		return
	if checkTcpStatus()[-1].startswith('STATE: IP INITIAL'):
		submitAT('AT+CSTT="telkomsel","wap","wap123"')
	if checkTcpStatus()[-1].startswith('STATE: IP START'):
		submitAT('AT+CIICR')
	if checkTcpStatus()[-1].startswith('STATE: IP GPRSACT'):
		resp = submitAT('AT+CIFSR', waitForResponse=False)
		
def closeConnection():
	submitAT('AT+CIPSHUT', 'SHUT OK')

def sendMessageInQueue():	
	while True:
		if r.llen('mq') > 0:
			msg = r.lrange('mq', 0, 0)[0]
			logger.debug('SENDMESSAGEINQUEUE: msg in queue: %s %s' % (r.llen('mq'), repr(msg)))
			try:				
				eventSIM908Ready.wait()				
				currentState = checkTcpStatus()[-1]
				logger.info('current state is: %s (%s) %s' % (currentState, len(currentState), currentState.strip() in ['STATE: PDP DEACT']))
				
				if currentState.strip() in [
					'STATE: IP INITIAL', 'STATE: IP START', 'STATE: IP GPRSACT', 
					'STATE: IP STATUS', 'STATE: TCP CLOSED', 'STATE: IP CLOSE'
					]:
					if submitAT('AT+CGATT?', '+CGATT: 1'):
						if submitAT('AT+QIOPEN="TCP","%s","%s"' % (config.server_ip, config.server_port), 'CONNECT OK'):
							currentState = checkTcpStatus()[-1]

				if currentState.strip() in ['STATE: PDP DEACT', 'STATE: TCP CONNECTING', 'STATE: IP IND']:
					logger.debug('got here')
					submitAT('AT+QIDEACT', 'DEACT OK')
					if submitAT('AT+CGATT?', '+CGATT: 1'):
						if submitAT('AT+QIOPEN="TCP","%s","%s"' % (config.server_ip, config.server_port), 'CONNECT OK'):
							currentState = checkTcpStatus()[-1]
	
				if currentState.startswith('STATE: CONNECT OK'):
					if submitAT('AT+QISEND', '>'):
						if not submitAT(msg + chr(26), 'SEND OK'):					
							logger.error('SENDMESSAGEINQUEUE: Cannot send msg, leave it in queue (%s)..' % r.llen('mq'))
							continue
						else:
							# remove message from queue
							r.lpop('mq')
							r.save()
							logger.debug('SENDMESSAGEINQUEUE: successed, remove from queue %s' % r.llen('mq'))
							# remove message from queue
							gevent.sleep(3)
							continue
				logger.error('SENDMESSAGEINQUEUE: Cannot send msg, leave it in queue (%s)..' % r.llen('mq'))
				
			except:
				logger.error('SENDMESSAGEINQUEUE: Cannot send msg, leave it in queue (%s)..' % r.llen('mq'))
				e = sys.exc_info()
				logger.error('SENDMESSAGEINQUEUE: Error: %s %s' % (e[0], e[1]))
		
		# sleep 3 seconds
		gevent.sleep(3)
		
def sendGPSInfo():
	while True:
		eventgpsFix.wait()
		try:
			if lastpos:
				# ITPRO861001000786141,11025.595867,-659.625256,31,20121008035615.000,15,0,13,1,
				gprmclon = 100 *(int(lastpos['lon']) + ((lastpos['lon'] - int(lastpos['lon'])) / 100 * 60))
				gprmclat = 100 *(int(lastpos['lat']) + ((lastpos['lat'] - int(lastpos['lat'])) / 100 * 60))
				gpsmsg = 'ITPRO%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,\r\n' % (
					imei, 
					gprmclon, 
					gprmclat,
					lastpos['alt'], 
					time.strftime("%Y%m%d%H%M%S", time.gmtime(lastpos['gpsdt'])), 
					lastpos['no_sat'], 
					lastpos['speed'], 
					lastpos['bearing'],
					'A',
					lastpos['ext_power'],
					'',
				)
				logger.debug('SENDGPSINFO: %s' % gpsmsg)
				r.rpush('mq', gpsmsg)
				#~ sendMessage('ITPRO%s,%s,%s,%s,%s,%s,%s,%s,%s' % 
					#~ (imei, gprmclon, gprmclat, lastpos['alt'], time.strftime("%Y%m%d%H%M%S.000", time.gmtime(lastpos['gpsdt'])), lastpos['no_sat'], lastpos['speed'], lastpos['bearing'], lastpos['ext_power'])
				#~ )
			gevent.sleep(60)
		except Exception:
			e = sys.exc_info()
			logger.error('SENDGPSINFO: Error sending GPS info: %s %s' % (e[0], e[1]))
			gevent.sleep(3)

def serialReader():
	eventSerialReady.wait()
	while True:
		try:
			result = ser.readlines()
			if result:
				logger.debug('SERIALREADER: got %s' % result)
				ares.set(result);
		except Exception:
				e = sys.exc_info()
				logger.error('HANDLEREQUEST: Error getting GPS info: %s %s' % (e[0], e[1]))

		gevent.sleep(0)

ares = AsyncResult()
eventSIM908Ready = Event()
eventSerialReady = Event()
eventgpsFix = Event()
eventSerialAvailable = Event()
gevent.joinall([
	gevent.spawn(initSIM908),
	gevent.spawn(serialReader),
	gevent.spawn(sendMessageInQueue),
])
closeConnection()
pub_socket.close()
ser.close()
