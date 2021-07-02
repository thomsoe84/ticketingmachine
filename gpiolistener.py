from PyQt4 import QtCore, QtNetwork
import RPi.GPIO as GPIO
import sys
import time

import logging
logger = logging.getLogger('root')

class GPIOListener(QtCore.QThread):
	destinationPressed = QtCore.pyqtSignal(str)
	printPressed = QtCore.pyqtSignal()
	directionSwitched = QtCore.pyqtSignal(bool)
	
	def __init__(self, destinations):
		QtCore.QThread.__init__(self)
		GPIO.setmode(GPIO.BCM)
		GPIO.cleanup()

		self.buttons = [22 ,27 ,17 ,4 ,3 ,2]
		self.buttonPrint = 10
		self.switchDirection = 9
		self.buzzer = 11

		self.time = time.time()

		GPIO.setup(self.buzzer, GPIO.OUT)

		for i in self.buttons:
			GPIO.setup(i,GPIO.IN,pull_up_down=GPIO.PUD_UP)
			GPIO.add_event_detect(i, GPIO.RISING, callback=self.destination_pressed, bouncetime=100)

		GPIO.setup(self.buttonPrint, GPIO.IN,pull_up_down=GPIO.PUD_UP)
		GPIO.add_event_detect(self.buttonPrint, GPIO.RISING, callback=self.print_pressed, bouncetime=200)

		GPIO.setup(self.switchDirection, GPIO.IN,pull_up_down=GPIO.PUD_UP)
		GPIO.add_event_detect(self.switchDirection, GPIO.BOTH, callback=self.direction_switched, bouncetime=200)

		self.destinations = destinations
		if len(self.destinations) > len(self.buttons):
			logger.error('Number of destinations (%s) bigger than the same as number of buttons (%s)' % (len(destinations), len(self.buttons)))
		logger.info("Listening to gpio updates..")

	def destination_pressed(self, channel):
		if (time.time() - self.time) > .5:
			self.time = time.time()
			logger.debug('button %s pressed' % channel)
			# check if button index within destination range
			if self.buttons.index(channel) < len(self.destinations):
				self.destinationPressed.emit(self.destinations[self.buttons.index(channel)])
			else:
				self.destinationPressed.emit('')
			self.buzz()

	def print_pressed(self, channel):
		if (time.time() - self.time) > .5:
			self.time = time.time()
			logger.debug('button Print %s pressed' % channel)
			self.printPressed.emit()
			self.buzz()

	def direction_switched(self, channel):
		if (time.time() - self.time) > .5:
			self.time = time.time()
			logger.debug('direction switched %s' % channel)
			self.directionSwitched.emit(GPIO.input(self.switchDirection))
			self.buzz()

	def buzz(self):
		GPIO.output(self.buzzer, True)
		time.sleep(.1)
		GPIO.output(self.buzzer, False)

			
	def __del__(self):
		self.wait()
	
	def run(self):
		pass	

def destPressed(dest):
	logger.debug(dest)

def prnPressed():
	logger.debug('Print pressed')

def dirSwitched(direction):
	logger.debug('Switched direction to %s' % direction)
	
if __name__ == '__main__':
	import logging.handlers
	logger.setLevel(logging.DEBUG)
	formatter = logging.Formatter('%(asctime)s %(thread)d %(levelname)-5s %(message)s')
	fh = logging.handlers.RotatingFileHandler('logGPIO.txt', maxBytes=10000000, backupCount=5)
	fh.setFormatter(formatter)
	ch = logging.StreamHandler()
	ch.setFormatter(formatter)
	logger.addHandler(fh)
	logger.addHandler(ch)
	# start new thread to listen to gpio signal
	gpioListener = GPIOListener(['A', 'B', 'C', 'D', 'E', 'F'])
	gpioListener.destinationPressed.connect(destPressed)
	gpioListener.printPressed.connect(prnPressed)
	gpioListener.directionSwitched.connect(dirSwitched)
	#~ QtCore.QTimer.singleShot(0, gpsThread.start)
	gpioListener.start()
	
	app = QtCore.QCoreApplication(sys.argv)
	sys.exit(app.exec_())
