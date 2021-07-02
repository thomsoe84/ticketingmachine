import RPi.GPIO as GPIO
import time
import config
import gevent
import sys
import logging
import logging.handlers

logger = logging.getLogger('')
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s %(levelname)-5s %(message)s')
fh = logging.handlers.RotatingFileHandler('logGPIODriver.txt', maxBytes=10000000, backupCount=5)
fh.setFormatter(formatter)
ch = logging.StreamHandler()
ch.setFormatter(formatter)
logger.addHandler(fh)
logger.addHandler(ch)

GPIO.setmode(GPIO.BCM)
GPIO.cleanup()

buttons = [22 ,27 ,17 ,4 ,3 ,2]
buttonPrint = 10
switchDirection = 9
buzzer = 11

lastSwitchState = True

for i in buttons:
	GPIO.setup(i,GPIO.IN,pull_up_down=GPIO.PUD_UP)
GPIO.setup(buttonPrint, GPIO.IN,pull_up_down=GPIO.PUD_UP)
GPIO.setup(switchDirection, GPIO.IN,pull_up_down=GPIO.PUD_UP)
GPIO.setup(buzzer, GPIO.OUT)

def monitorIO():
	while True:
		for i in buttons:
			if not GPIO.input(i):
				logger.debug( 'button %s pressed' % buttons.index(i))
				#pub_socket.send_pyobj(buttons.index(i))
				buzz()
				gevent.sleep(.5)
		
		if not GPIO.input(buttonPrint):
			logger.debug('button Print pressed')
			#pub_socket.send_pyobj(buttonPrint)
			buzz()
			gevent.sleep(1.5)
		
		curSwitchState = GPIO.input(switchDirection)
		global lastSwitchState
		if lastSwitchState != curSwitchState:
			if curSwitchState:				
				#pub_socket.send_pyobj(-1)
				pass
			else:
				#pub_socket.send_pyobj(-2)
				pass
			buzz()
			logger.debug('switched to %s' % curSwitchState)
		lastSwitchState = curSwitchState
		
		print "MonitorIO before sleep"
		gevent.sleep(.02)

def buzz():
	GPIO.output(buzzer, True)
	gevent.sleep(.1)
	GPIO.output(buzzer, False)



print "before joinall"
gevent.joinall([
	gevent.spawn(monitorIO),
	
])

print 'after joinall'
