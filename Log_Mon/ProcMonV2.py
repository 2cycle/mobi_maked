#!/usr/bin/env python
#-*- coding: utf-8 -*-
# vim: ai noet ts=4 sts=4 sw=4 nu nowrap

import os
import sys
import time
import signal
import ConfigParser
import traceback
import cStringIO
import MySQLdb
import socket
import shlex
import glob
import pexpect
from datetime import datetime, timedelta, date

import logging
import logging.config

logging.basicConfig(stream = sys.stderr, level=logging.DEBUG, format='%(message)s')
logger = logging.getLogger()

SHUTDOWN = False

HOST = None
HOST_IP = None
cfg = None

def shutdown(sigNum, f) :
	global SHUTDOWN
	SHUTDOWN = True

# signal
signal.signal(signal.SIGTERM, shutdown)	 # Sig Terminate: 15
signal.signal(signal.SIGINT, shutdown)	  # Sig Inturrupt: 2
try :
	signal.signal(signal.SIGHUP, shutdown)  # Sig HangUp: 1
except Exception, e : pass
try :
	signal.signal(signal.SIGPIPE, shutdown) # Sig Broken Pipe: 13
except Exception, e : pass

def get_err():
	buf = cStringIO.StringIO()
	traceback.print_exc(file=buf)
	msg = buf.getvalue()
	buf.close()
	return msg

def initLog(cfg):
	log_name = cfg.get('DB', 'log_path')
	LOGGING_CONF = {
		'version': 1,
		'disable_existing_loggers': False,
		'formatters':{
			'fmt_console':{
				'format':'%(asctime)s %(levelname)s [%(name)s] %(message)s'
			},
			'fmt_rolling':{
				'format':'[%(asctime)s] %(process)d, "%(filename)s", %(lineno)s, %(funcName)s : %(message)s',
				'datefmt': '%Y/%m/%d %H:%M:%S'
			}
		},
		'handlers':{
			'console':{
				'level': 'DEBUG',
				'class': 'logging.StreamHandler',
				'formatter': 'fmt_console',
				'stream': 'ext://sys.stdout',
			},
			'rolling': {
				'level': 'DEBUG',
				'class': 'logging.handlers.RotatingFileHandler',
				'formatter': 'fmt_rolling',
				'filename': log_name,
				'mode': 'a',
				'maxBytes': 1024*1024*10,
				'backupCount': 10
			}
		},
		'loggers':{
			'': {
				'level': 'DEBUG',
				'handlers': ['console', 'rolling']
			},
			'EventClient': {
				'level': 'DEBUG',
				'handlers': ['console', 'rolling']
			}
		}
	}
	logging.config.dictConfig(LOGGING_CONF)

#def initLog(cfg):
#       log_path = cfg.get('DB', 'log_path')
#       local_makedirs(log_path)
#       log_name = os.path.join(
#	       log_path,
#	       '%s.log' % (os.path.basename(sys.argv[0])),
#       )
#       Log.Init(Log.CRotatingLog(log_name, 1000000, 10))


def insert_db(param_list, event_time):
	conn = None
	cursor = None
	try:
		conn = MySQLdb.connect(
			host=cfg.get('DB', 'host'),
			user=cfg.get('DB', 'user'),
			passwd=cfg.get('DB', 'passwd'),
			db=cfg.get('DB', 'db'),
			charset=cfg.get('DB', 'charset'),
			use_unicode = cfg.getboolean('DB', 'use_unicode')
		)
		conn.autocommit = False
		#print cfg.get('DB', 'sql', 1)
		cursor = conn.cursor()

		if len(param_list) > 0:
			cursor.executemany(cfg.get('DB', 'sql_insert', 1), param_list)

		cursor.execute(cfg.get('DB', 'sql_delete', 1), (event_time, HOST))
		logger.info('[update] host:%s cnt:%s' % (HOST, len(param_list)))

	except Exception as e:
		conn.rollback()
		raise e
	finally:
		conn.commit()
		if cursor:
			cursor.close()
		if conn:
			conn.close()

def run_cmd(cmd, passwd=None, timeout=None):

	buf = cStringIO.StringIO()

	try:
		logger.info('cmd:%s' %cmd)

		child = pexpect.spawn('/bin/bash', ['-c', cmd], timeout=timeout)
		#if not passwd:
		#       child.logfile=buf

		child.logfile=buf

		expect_list = [
			pexpect.EOF,
			pexpect.TIMEOUT,
			r'Are you sure you want to continue connecting \(yes/no\)\?',
			'Permission denied',
			'[Pp]assword: '
		]


		i = child.expect(expect_list)

		if i == 0: # EOF: no password cmd
			msg = 'Success'
			child.close()
			if child.exitstatus != 0:
				msg = child.before

			output = buf.getvalue()
			buf.close()

			return {
				'success': True,
				'msg': msg,
				'exit_status': child.exitstatus,
				'output': output,
			}
		elif i == 1: # Timeout
			logger.error('Timeout')
			child.close()

			output = buf.getvalue()
			buf.close()

			return {
				'success': False,
				'msg' : 'Timeout',
				'exit_status': child.exitstatus,
				'output': output,
			}
		elif i == 2: # SSH does not have the public key. Just accept it.
			child.sendline('yes')
			if passwd:
				child.expect('[Pp]assword: ')
		elif i == 3: # Permission denied
			logger.error('Permission denied')
			child.close()

			output = buf.getvalue()
			buf.close()

			return {
				'success': False,
				'msg': 'Permission denied',
				'exit_status': child.exitstatus,
				'output': output,
			}

		if passwd:
			child.sendline(passwd)

		#child.logfile=sys.stdout

		i = child.expect([pexpect.EOF,'Permission denied'], timeout=timeout)

		if i == 0:
			msg = 'Success'
			child.close()
			if child.exitstatus != 0:
				msg = child.before

			output = buf.getvalue()
			buf.close()

			return {
				'success': True,
				'msg': msg,
				'exit_status': child.exitstatus,
				'output': output,
			}
		elif i == 1: # Incorrect Password
			msg = 'Incorrect Password'
			child.close()
			if child.exitstatus != 0:
				msg = msg

			output = buf.getvalue()
			buf.close()

			return {
				'success': False,
				'msg': msg,
				'exit_status': child.exitstatus,
				'output': output,
			}


	except Exception as e:
		logger.error(get_err())

		output = buf.getvalue()
		buf.close()

		return {
			'success': False,
			'msg': str(e),
			'exit_status': child.exitstatus,
			'output': output,
		}

def parse_mf(data, ports):
	b_head = True
	head = None
	ret = {}
	portidx = 0
	for line in data.split('\n'):
		if not line or not line.strip():
			continue
		if line.startswith('<end>') :
			portidx = portidx + 1
		if line.startswith('-')  \
			or line.startswith('<end>'):
			continue
		if line.startswith('<begin>'):
			b_head = True
			continue

		if b_head:
			head = [name.strip() for name in line.split('|')]
			b_head = False
			continue

		info = {}

		info['SIOEF_PORT'] = ports[portidx]
		cols = [x.strip() for x in line.split('|', len(head)-1)]
		for i,h in enumerate(head):
			info[h] = cols[i]

		# remove 'java -Xms32m -Xmx64m -jar'
		if '-jar' in  info['PROGRAM_NAME'] :
			info['PROGRAM_NAME'] =  (' ').join( info['PROGRAM_NAME'].split(' ')[4:6])
		ret[info['PROGRAM_NAME']] = info
	return ret

def parse_pf(data):
	ret = {}
	b_first = True
	for line in data.split('\n'):
		if b_first:
			b_first = False
			continue
		if not line:
			continue
		sline = line.strip()
		if not sline:
			continue
		pid, pcpu, pmem, size, cmd = sline.split(None, 4)
		ret[pid] = {
			'pid': pid,
			'pcpu': float(pcpu),
			'pmem': float(pmem),
			'size': float(size)/1024.,
			'cmd': cmd,
		}

	return ret

def work():
	seconds = 0

	'''
	while not SHUTDOWN:

		try:
			work_host()
		except Exception as e:
			logger.error(get_err())

		for i in range(sleep_sec):
			if SHUTDOWN:
				return
			time.sleep(1)
	'''
	try:
		work_host()
	except Exception as e:
		logger.error(get_err())



def work_host():
	cmd_sleep_sec = cfg.getint('DB', 'cmd_sleep_sec')
	mf_port_list = cfg.get(HOST, 'mf_port_list')
	port_list = [port.strip() for port in mf_port_list.split(',')
		if port and port.strip()]

	pair = [{}, {}]

	for i in range(len(pair)):
		output = []
		ports = []
		for port in port_list:
			out = run_cmd('mf %s' % port)
			output.append(out['output'])
			ports.append(port)
			print 'mf get port : %s' % port

		pair[i] = parse_mf('\n'.join(output), ports)
		if i==0:
			time.sleep(cmd_sleep_sec)
	ps_dict = parse_pf(run_cmd('ps -A -o pid,pcpu,pmem,size,cmd')['output'])

	event_time = datetime.now().strftime('%Y%m%d%H%M%S')
	#print pair
	first,second = pair

	param_list = []
	for k,v in second.items(): #
		vs = v  # second
		vf = first.get(k, {}) #

		vf_status = vf.get('STATUS', '')
		vs_status = vs.get('STATUS', '')

		ps_info = ps_dict.get(vs.get('PID', ''), {})

		#print v


		status = vs_status[:3]
		if vs_status.startswith('ACT') \
			and vf_status.startswith('ACT'):
			vf_re_cnt = int(vf_status[4:4+3]) # ACT(002) => 002
			vs_re_cnt = int(vs_status[4:4+3]) # ACT(002) => 002
			if vs_re_cnt - vf_re_cnt > 1: # restart
				status = 'ABN'

		SIOEF_PORT = vf.get('SIOEF_PORT')

		param = (
			event_time,
			HOST,
			HOST_IP,
			SIOEF_PORT,
			vs['PROGRAM_NAME'],
			status,
			ps_info.get('pcpu', 0.0),
			ps_info.get('pmem', 0.0),
			ps_info.get('size', 0.0),
		)*2

		param_list.append(param)
	insert_db(param_list, event_time)


	#print out





def main():
	global cfg, HOST, HOST_IP
	if len(sys.argv) < 2:
		print 'Usage: ProcMon.py ProcMon.conf'
		return

	try:
		HOST = socket.getfqdn()
		HOST_IP = socket.gethostbyname(HOST)

		cfg = ConfigParser.ConfigParser()
		cfg.read(sys.argv[1])

		initLog(cfg)

		logger.info('start HOST:%s' % HOST)
		#__LOG__.Trace('start HOST:%s' % HOST)

		work()

	except Exception as e:
		logger.error('', exc_info=1)
		#__LOG__.Trace(get_err())
		sys.exit()

if __name__ == '__main__':
	main()


