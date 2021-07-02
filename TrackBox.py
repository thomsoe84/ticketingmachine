import pygame
from pygame.locals import *
from pygame.color import THECOLORS

class TrackBox:
	
	def __init__(self, screen, route, POIs, size, posX, posY):
		self.screen = screen
		self.x = posX
		self.y = posY
		self.size = size
		self.route = route
		self.POIs = POIs
		self.bgsurface = pygame.Surface((size[0], size[1]))
		
		self.marginLR = 30
		self.stopFontSize = 16
		self.linePosY = self.bgsurface.get_height() / 2
		
		self.drawBackground()		
	
	def drawBackground(self):
		self.bgsurface.fill(THECOLORS['black'])		
		self.linelength = self.size[0] - (2 * self.marginLR)
		pygame.draw.line(self.bgsurface, THECOLORS['green'], (self.marginLR, self.linePosY), (self.marginLR + self.linelength, self.linePosY))
		
		alternateUpDown = True
		prevUpRightX = 0
		prevDownRightX = 0
		wasDownDown = False
		wasUpUp = False
		stopFont = pygame.font.Font(None, self.stopFontSize)
		#~ for dest in self.route.getDestinations():
		for dest in self.POIs:
			textSurface = stopFont.render(
				dest, 
				True, 
				THECOLORS['black'],
				THECOLORS['yellow'], 	# background color
			)
			#~ distanceDestFactor = self.route.simpleDistanceTo(self.route.getDestinations()[dest]['latlon'], normalized = True)
			distanceDestFactor = self.route.simpleDistanceTo(self.POIs[dest]['latlon'], normalized = True)
			posLineX = self.marginLR + (distanceDestFactor * self.linelength)
			posTextX = posLineX
			if (posTextX - int(textSurface.get_width() / 2)) < 0:
				# first text
				posTextX = 0
			elif (posTextX + int(textSurface.get_width() / 2)) > self.size[0]:
				posTextX = self.size[0] - textSurface.get_width()
			else:
				posTextX = posTextX - int(textSurface.get_width() / 2)
			posTextY = 0
			if alternateUpDown:
				# text below line
				if wasDownDown or ((posTextX - self.marginLR) >= prevDownRightX):
					posTextY = self.linePosY + 10
					wasDownDown = False
				else:
					posTextY = self.linePosY + 10 + self.stopFontSize
					wasDownDown = True
			else:
				# text above line
				if wasUpUp or ((posTextX - self.marginLR) >= prevUpRightX):
					posTextY= self.linePosY - (6 + self.stopFontSize)
					wasUpUp = False
				else:
					posTextY= self.linePosY - (6 + (2 *self.stopFontSize))
					wasUpUp = True
					
			self.bgsurface.blit(textSurface, 
				(posTextX, posTextY)
			)

			pygame.draw.line(self.bgsurface, THECOLORS['yellow'], 
				(posLineX, self.linePosY), 
				(posLineX, posTextY if alternateUpDown else posTextY + self.stopFontSize - 4)
			)
			
			if alternateUpDown:
				prevDownRightX = posTextX - self.marginLR + self.bgsurface.get_width()
			else:
				prevUpRightX = posTextX - self.marginLR + self.bgsurface.get_width()	
			
			alternateUpDown = not alternateUpDown
		
		self.bgsurface = self.bgsurface.convert()
		self.screen.blit(self.bgsurface, (self.x, self.y))
		pygame.display.update()

	def updatePosition(self, newpos):
		toblitSurface = self.bgsurface.copy()
		progress = self.route.simpleDistanceTo((newpos['lon'], newpos['lat']), normalized = True)
		pygame.draw.polygon(toblitSurface, THECOLORS['red'], [
			(self.marginLR+int(self.linelength*progress) -10, self.linePosY - 8 ),
			(self.marginLR+int(self.linelength*progress) +10, self.linePosY ),
			(self.marginLR+int(self.linelength*progress) -10, self.linePosY + 8 ),
			(self.marginLR+int(self.linelength*progress), self.linePosY ),
		])
		self.screen.blit(toblitSurface, (self.x, self.y))
		pygame.display.update()
		
		

