import pygame
from pygame.locals import *
from pygame.color import THECOLORS

class ListBox:
	pageNo = 0
	fontSize = 54
	prevItem = ' <<<'
	nextItem = ' >>>'
	bgcolor = THECOLORS['black']
	selectedItem = None
	distanceBetweenItem = 0.42
	
	def __init__(self, screen, items, rowNo, posX, posY):
		self.screen = screen
		self.x = posX
		self.y = posY
		self.items = items
		self.rowNo = rowNo
		self.font = pygame.font.Font(None, self.fontSize)
		self.surface = pygame.Surface((500, int(self.rowNo * self.fontSize * (1.0 + self.distanceBetweenItem))))
		self.draw()
		
	def getItemsByPage(self, pageNo):
		if pageNo == 0:
			if len(self.items) <= self.rowNo:
				return self.items
			else:
				return self.items[0:(self.rowNo-1)] + [self.nextItem]
		else:
			toreturn = [self.prevItem]
			firstIndex = 0 if pageNo == 0 else (self.rowNo-1) + ((pageNo-1)*(self.rowNo-2))
				
			for i in xrange(firstIndex, firstIndex + (self.rowNo -2), 1):
				if i < len(self.items):
					toreturn.append(self.items[i])
			
			if firstIndex + (self.rowNo - 1) == len(self.items):
				toreturn.append(self.items[firstIndex + (self.rowNo -2)])
			elif firstIndex + (self.rowNo - 1) < len(self.items):
				toreturn.append(self.nextItem)
				
			return toreturn

	def draw(self):
		self.surface.fill(self.bgcolor)
		yoffset = 0
		for i, item in enumerate(self.getItemsByPage(self.pageNo)):
			textSurface = self.font.render(
				'%s' % (item), 
				True, 
				THECOLORS['green'] if item in [self.prevItem, self.nextItem] else 
					THECOLORS['white'] if item != self.selectedItem else THECOLORS['black'] , 	# font color
				THECOLORS['black'] if item != self.selectedItem else THECOLORS['white'] , 	# background color
			)
			self.surface.blit(textSurface, (0, yoffset))
			yoffset += self.fontSize + (self.distanceBetweenItem * self.fontSize)
		
		self.screen.blit(self.surface, (self.x, self.y))
		pygame.display.update()
	
	def selectRow(self, iRow):
		part_items = self.getItemsByPage(self.pageNo)
		if iRow > (len(part_items) - 1):
			self.selectedItem = None
			return
		item = part_items[iRow]
		if item == self.prevItem:
			self.pageNo -= 1
			self.selectedItem = None
		elif item == self.nextItem:
			self.pageNo += 1	
			self.selectedItem = None
		else:
			self.selectedItem = item
		self.draw()
	
	def getSelected(self):
		return self.selectedItem
		
	def getItems(self):
		return self.items
	
	def setItems(self, items):
		self.items = items
		self.pageNo = 0
		if not self.selectedItem in self.items:
			self.selectedItem = None
		self.draw()

