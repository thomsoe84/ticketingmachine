import shapely
from shapely.geometry import Point, Polygon, LineString
import ruteSmgCilacap
from pyproj import Proj
import math
from matplotlib import pyplot
import pygame
from pygame.locals import *
from pygame.color import THECOLORS
import zmq
import time

context = zmq.Context()
pub_socket = context.socket(zmq.PUB)
pub_socket.bind("tcp://*:5600")

def utmzone(lon):
	return math.floor((lon + 180) / 6 + 1)
	
proj = Proj(proj='utm',zone=utmzone(ruteSmgCilacap.route[0][0]),ellps='WGS84')
#~ proj = Proj(init="epsg:3785")  # spherical mercator, should work anywhere...

ruteSmgCilacap_cart = []
for point in ruteSmgCilacap.route:
	ruteSmgCilacap_cart.append(proj(point[0], point[1]))

#~ print ruteSmgCilacap_cart
#~ route = LineString(ruteSmgCilacap.route)
route = LineString(ruteSmgCilacap_cart)
#~ print route.length

agents = {
	"Garasi Pudakpayung": (110.4099235777,-7.0989063755),
	"Terminal Terboyo": (110.462975744158, -6.95384580641985), 
	"Cilacap": (109.0249472670, -7.7022626717), 
	"Kutoarjo": (109.9062432814, -7.722858265), 
	"Terminal Bawen": (110.4337694217, -7.245006552), 
	"Sukun": (110.413206936792, -7.06509461626411), 
	"Karanganyar": (109.588919011876, -7.65229370445013), 
	"Terminal Kebumen": (109.678658265621, -7.69742991775275), 
	"Kutowinangun": (109.736100118607, -7.72165780887008), 
	"Leo Prembun": (109.802533071488, -7.72449005395174), 
	"RM Ngandong": (109.881962416694, -7.72480747662485), 
	"Brengkelan": (110.01927902922, -7.70454799756408), 
	"Terminal Purworejo": (109.967464953661, -7.72800751961768), 
	"Gombong": (109.507830636576, -7.60913721285761), 
	"Tambak": (109.397742636502, -7.61323562823236), 
	"Sumpiuh": (109.360492117703, -7.61254906654358), 
	"Buntu": (109.252259619534, -7.58980385027826), 
	"Sampang": (109.184698378667, -7.56850183010102), 
	"Maos": (109.13994429633, -7.62021213769913), 
	"Kaliboto": (110.049211895093, -7.65045982785523), 
	"Tanjung / Magelang": (110.187828456983, -7.52463195472956),
}

agents_cart = {}
for agent in agents:
	obj_proj = proj(agents[agent][0], agents[agent][1])
	agents_cart[agent] = Point(obj_proj[0], obj_proj[1])

def cut(line, distance):
    # Cuts a line in two at a distance from its starting point
    if distance <= 0.0 or distance >= line.length:
        return [LineString(line)]
    coords = list(line.coords)
    for i, p in enumerate(coords):
        pd = line.project(Point(p))
        if pd == distance:
            return [
                LineString(coords[:i+1]),
                LineString(coords[i:])]
        if pd > distance:
            cp = line.interpolate(distance)
            return [
                LineString(coords[:i] + [(cp.x, cp.y)]),
                LineString([(cp.x, cp.y)] + coords[i:])]

def distanceTo(route, city, actual):
	print 'to city: %s to actual: %s' % (route.project(city) , route.project(actual))
	if route.project(city) > route.project(actual):
		print "city further"
		routeToCity = cut(route, route.project(city))[0]
		return routeToCity.length - routeToCity.project(actual)
	elif route.project(city) < route.project(actual):
		print "actual further"
		routeToActual = cut(route, route.project(actual))[0]
		return routeToActual.length - routeToActual.project(city)
	else:
		return 0.0

#~ print route.project(Point(13,0))
#~ print distanceTo(route, jogja, semarang)

def plot_line(ax, ob, color='#999999'):
    # Plot a line
    x, y = ob.xy
    ax.plot(x, y, color=color, alpha=0.7, linewidth=2, solid_capstyle='round', zorder=2)

def onclick(event):
	#~ print 'button=%d, x=%d, y=%d, xdata=%f, ydata=%f'%(event.button, event.x, event.y, event.xdata, event.ydata)
	print distanceTo(route, agents_cart['Cilacap'], Point(event.xdata, event.ydata))
	global bus
	curpos = route.interpolate(route.project(Point(event.xdata, event.ydata)))
	curpos_lonlat = proj(curpos.x, curpos.y, inverse=True)
	msg = {'type': 0, "lat": curpos_lonlat[1], "speed": 30.2, "lon": curpos_lonlat[0], "bearing": 170, "alt": 50.2, "gpsdt": time.time(), 'imei': 'pyplot_sim'  }
	pub_socket.send_pyobj(msg)
	ax.lines.remove(bus)
	bus, = ax.plot(curpos.x, curpos.y, 'bo')
	fig.canvas.draw()
	
fig = pyplot.figure()
ax = fig.add_subplot(111)
plot_line(ax, route)
for agent in agents:
	position_cart = proj(agents[agent][0], agents[agent][1])
	ax.plot(position_cart[0], position_cart[1] , 'r^')
	ax.annotate(agent, (position_cart[0], position_cart[1]))

bus, = ax.plot(agents_cart['Terminal Terboyo'].x, agents_cart['Terminal Terboyo'].y, 'bo')
print bus
cid = fig.canvas.mpl_connect('button_press_event', onclick)

#~ pyplot.set_aspect(1)
pyplot.show()