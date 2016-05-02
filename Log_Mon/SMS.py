import os
import sys
import time
import signal
from socket import *
import ConfigParser
import Mobigen.Common.Log as Log


def __init(self):
	print "start SMS"	


def Connect(HOST, PORT):
	#stream socket start
	sock = socket(AF_INET, SOCK_STREAM)
	ADDR =(HOST, PORT)
	try:

		sock.connect(ADDR)
 
	except Exception:
		print "SMS Server Connect Fail"
		return False
	return sock

def SendMessage(to_num, msg, HOST,PORT,from_num):

	sock = Connect(HOST,PORT)
	print "connect"
	to_num = to_num.split()
	number= map(str,to_num)
	if not sock:
		print "**** Process end ****"
		sys.exit(-1)
	print "**** SMS Server Connect ****"
	
	
	for i in number:
		sock = Connect(HOST,PORT)	

		print "SEND-SMS %s %s %s" % (from_num, i, msg)
		sock.send("SEND-SMS %s %s, %s\r\n" % (from_num, i, msg) )
		sock.close()
	sock.close()	

		
		
