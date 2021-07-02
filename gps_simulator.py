import zmq
import time

context = zmq.Context()
pub_socket = context.socket(zmq.PUB)
pub_socket.bind("tcp://*:5600")

def log(tolog):
	print tolog
	
while True:
	msg = {"lat": -7.06509461626411, "speed": 30.2, "lon": 110.413206936792, "bearing": 170, "alt": 50.2, "gpsdt": time.time() }
	log(msg)
	pub_socket.send_pyobj(msg)
	time.sleep(1)
	