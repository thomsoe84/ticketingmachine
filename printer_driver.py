import serial

class PrinterC1:
	def __init__(self, port, baudrate):
		self.ser = serial.Serial(port=port, baudrate=baudrate)
		self.ser.write(chr(27) + chr(64))		# initialize printer
		self.selectFont1(0)
		self.setGrayDegree(4)

	def close(self):
		self.ser.close()

	def selectFont1(self, n):
		self.ser.write(chr(27) + chr(54) + chr(n))

	def lineFeed(self, n):
		for i in xrange(n):
			self.ser.write(chr(10))

	def dotLineFeed(self, n):
		self.ser.write(chr(27) + chr(74) + chr(n))

	def setDotLineSpacing(self, n):
		self.ser.write(chr(27) + chr(49) + chr(n))

	def setSpaceBetweenCharacters(self, n):
		self.ser.write(chr(27) + chr(112) + chr(n))

	def printBlankChar(self, n):
		self.ser.write(chr(27) + chr(102) + chr(0) + chr(n))
		
	def printBlankLine(self, n):
		self.ser.write(chr(27) + chr(102) + chr(1) + chr(n))

	def setRightMargin(self, n):
		self.ser.write(chr(27) + chr(81) + chr(n))

	def setLeftMargin(self, n):
		self.ser.write(chr(27) + chr(108) + chr(n))

	def enlargeWidth(self, n):
		self.ser.write(chr(27) + chr(55) + chr(n))

	def enlargeHeight(self, n):
		self.ser.write(chr(27) + chr(56) + chr(n))

	def setCharacterRotationalPrint(self, n):
		self.ser.write(chr(28) + chr(73) + chr(n))

	def setGrayDegree(self, n):
		self.ser.write(chr(27) + chr(109) + chr(n))

	def cutPaper(self, n):
		self.lineFeed(10)
		self.ser.write(chr(27) + chr(107) + chr(n))
		
	def printBarcode(self, n, data):
		self.ser.write(chr(29) + chr(104) + chr(60))
		self.ser.write(chr(29) + chr(72) + chr(1))
		self.ser.write(chr(29) + chr(119) + chr(3))
		#~ self.ser.write(chr(29) + chr(87) + chr(2) + chr(8))
		self.ser.write(chr(29) + chr(107) + chr(n) + data + chr(0))

	def printString(self, toprint, widthfactor = 2, heightfactor = 2):
		self.ser.write(chr(27) + chr(55) + chr(widthfactor))
		self.ser.write(chr(27) + chr(56) + chr(heightfactor))
		self.ser.write(toprint)
		self.ser.write(chr(13))
		
	def allowPrinting(self):
		self.ser.write(chr(27) + chr(100) + chr(1))
	
	def forbidPrinting(self):
		self.ser.write(chr(27) + chr(100) + chr(0))
		

if __name__ == "__main__":
	p = PrinterC1('/dev/ttyS0', 9600)
	#p.lineFeed()
	#p.dotLineFeed(1)
	#p.setDotLineSpacing(3)
	#p.setSpaceBetweenCharacters(0)
	#p.printBlankChar(5)
	#p.setRightMargin(0)
	#p.setLeftMargin(0)
	#p.enlargeWidth(0)
	#p.enlargeHeight(0)
	#p.setCharacterRotationalPrint(0)
	import time
	curtime = time.time()
	p.selectFont1(2)
	p.printString( 'PO. Sumber Alam')
	p.printString( 'Terminal Terboyo', 2, 4)
	p.printString( time.strftime('%d-%b-%Y %H:%M', time.localtime(curtime)), 2, 4)
	p.printString( 'Rp. {:,.0f}'.format(18500), 2, 4)
	p.selectFont1(0)
	p.printString( 'Jarak: {:,.1f} km'.format(38.7))
	p.printString( 'Bus: AA2325BC')
	p.printBarcode(2, '%03d%010d' % (27, int(curtime)))
	p.cutPaper(0)
	p.close()
