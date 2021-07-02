import shapely
from shapely.geometry import Point, Polygon, LineString
from pyproj import Proj
import math



class Route:
	length = 0.0
	mode = '>'
	listPoints = []
	def __init__(self, listPoints, destinations, mode = '>'):
		self.listPoints = listPoints
		self.proj = Proj(proj='utm',zone=self.utmzone(self.listPoints[0][0]),ellps='WGS84')
		self.mode = mode
		
		self.routeCartesian = []
		ruteSmgCilacap_cart = []
		for point in self.listPoints:
			self.routeCartesian.append(self.proj(point[0], point[1]))
		
		self.route = LineString(self.routeCartesian)
		self.length = self.route.length / 1000
		
		self.destinations = destinations
		
	def switchDirection(self):		
		if self.mode == '>':
			self.mode = '<'
		else:
			self.mode = '>'
			
		self.routeCartesian = []
		ruteSmgCilacap_cart = []
		self.listPoints.reverse()
		for point in self.listPoints:
			self.routeCartesian.append(self.proj(point[0], point[1]))
		
		self.route = LineString(self.routeCartesian)
		self.length = self.route.length / 1000
		
	def utmzone(self, lon):
		return math.floor((lon + 180) / 6 + 1)
		
	def cut(self, line, distance):
		# Cuts a line in two at a distance from its starting point
		if distance <= 0.0 or distance >= line.length:
			return [LineString(line)]
		coords = list(line.coords)
		for i, p in enumerate(coords):
			pd = line.project(Point(p))
			if pd == distance:
				return [
					LineString(coords[:i+1]),
					LineString(coords[i:])
				]
			if pd > distance:
				cp = line.interpolate(distance)
				return [
					LineString(coords[:i] + [(cp.x, cp.y)]),
					LineString([(cp.x, cp.y)] + coords[i:])
				]
				
	def distanceTo(self, pointAlonlat, pointBlonlat):
		PointA_proj = self.proj(pointAlonlat[0], pointAlonlat[1])
		PointB_proj = self.proj(pointBlonlat[0], pointBlonlat[1])
		pointA = Point(PointA_proj[0], PointA_proj[1])
		pointB = Point(PointB_proj[0], PointB_proj[1])

		distA = self.route.project(pointA)
		distB = self.route.project(pointB)
		return (distB - distA) / 1000
			
	def simpleDistanceTo(self, pointLonLat, normalized = False):
		point_proj = self.proj(pointLonLat[0], pointLonLat[1])
		pointCart = Point(point_proj[0], point_proj[1])
		if normalized:
			return self.route.project(pointCart, normalized = True)
		else:
			return self.route.project(pointCart)/1000

	def getDestinations(self):
		if self.mode == '>':
			return self.destinations[0]
		else:
			return self.destinations[1]
		
	def getDestinationNames(self):
		if self.mode == '>':
			return self.destinations[0].keys()
		else:
			return self.destinations[1].keys()

# GPX to route
#~ f = open('rute_Smg_Cilacap.gpx', 'r')
#~ fout = open('ruteSmgCilacap.py', 'w')
#~ fout.write('route = [\n')
#~ for line in f:
	#~ if line.strip().startswith('<trkpt'):
		#~ spl = line.split('"')
		#~ fout.write('    (%s, %s),\n' % (spl[3], spl[1]))
#~ f.close()
#~ fout.write(']\n')
#~ fout.close()
#~ quit()
#~ route = LineString([
	#~ (13,0),(13,1),(12,2),(11,3),(10,4),(9,6),(8,7),(7,8),(6,8),(5,9),(4,10),(3,11),(2,12),(2,13),(2,14),(1,15),(0,15)
#~ ])



if __name__ == "__main__":
	import ruteSmgCilacap
	from collections import OrderedDict
	destinations = OrderedDict([
		("Terminal Terboyo", {'latlon':  (110.462975744158, -6.95384580641985)}), 
		("Sukun", {'latlon':   (110.413206936792, -7.06509461626411)}), 
		("Garasi Pudakpayung", {'latlon':   (110.4099235777,-7.0989063755)}),	
		("Terminal Bawen", {'latlon':   (110.4337694217, -7.245006552)}), 
		("Tanjung / Magelang", {'latlon':   (110.187828456983, -7.52463195472956)}),
		("Kaliboto", {'latlon':   (110.049211895093, -7.65045982785523)}), 
		("Brengkelan", {'latlon':   (110.01927902922, -7.70454799756408)}), 
		("Terminal Purworejo", {'latlon':   (109.967464953661, -7.72800751961768)}), 
		("Kutoarjo", {'latlon':   (109.9062432814, -7.722858265)}), 
		("RM Ngandong", {'latlon':   (109.881962416694, -7.72480747662485)}), 
		("Leo Prembun", {'latlon':   (109.802533071488, -7.72449005395174)}), 
		("Kutowinangun", {'latlon':   (109.736100118607, -7.72165780887008)}), 
		("Terminal Kebumen", {'latlon':   (109.678658265621, -7.69742991775275)}), 
		("Karanganyar", {'latlon':   (109.588919011876, -7.65229370445013)}), 
		("Gombong", {'latlon':   (109.507830636576, -7.60913721285761)}), 
		("Tambak", {'latlon':   (109.397742636502, -7.61323562823236)}), 
		("Sumpiuh", {'latlon':   (109.360492117703, -7.61254906654358)}), 
		("Buntu", {'latlon':   (109.252259619534, -7.58980385027826)}), 
		("Sampang", {'latlon':   (109.184698378667, -7.56850183010102)}), 
		("Maos", {'latlon':   (109.13994429633, -7.62021213769913)}), 	
		("Cilacap", {'latlon':   (109.0249472670, -7.7022626717)}), 	
	])
	route = Route(ruteSmgCilacap.route, destinations)
	#~ print route.length
	import cProfile
	cProfile.run('route.distanceTo((110.462975744158, -6.95384580641985), (109.0249472670, -7.7022626717))', 'routeproof.stat')
	import pstats
	p = pstats.Stats('routeproof.stat')
	p.sort_stats('time').print_stats(10)
	
	#~ print route.getDestinationNames()

	
