#!/bin/env python

# std
import os
import stat
import sys
import re
import getopt
import ConfigParser
import time
import signal
import struct
import select
from SMS import *

from threading import *
from socket import * 

# Mobigen
import Mobigen.Common.Log as Log
import Mobigen.Collector.ColTail as ColTail

# global
SHUTDOWN = False
def Shutdown(num = 0, frame = 0):
	global SHUTDOWN
	SHUTDOWN = True
	__LOG__.Trace("SIGNAL NUM:%s" % num)
	return

signal.signal(signal.SIGINT, Shutdown)
signal.signal(signal.SIGTERM, Shutdown)

#Detect 클래스 (Thread를 생성한다.)
class Detect(Thread):

	#Detect 생성자, 모든 값을 초기화한다.
	def __init__(self, target, config, tfile, tprtn, ttime,HOST,PORT,from_num):

		#Thread 시작
		Thread.__init__(self)
		#config에서 sms 리스트를 받아온다.
		self.smsList = config.options("SMS receive list")
		self.target = target
		self.tfile  = tfile
		self.tprtn  = tprtn
		self.ttime  = ttime
		self.config = config
		self.HOST = HOST
		self.PORT = PORT
		self.from_num = from_num

	#각파일별 line체크용 idx 읽기
	def LoadIdx(self):

		fp = open(self.idxFile, "r")
		idxRead =  fp.read()
		fp.close()
		return idxRead
	#idx값 수정
	def DumpIdx(self, lineNum):

		fp = open(self.idxFile, "w")
		fp.write(str(lineNum))
		fp.close()

	#process ID를 받아오는 메소드
	def GetPid(self):

		r = os.popen("ps -ef | grep tail | grep %s | grep -v sh" % self.tfile)
		
		pid = r.readline().split()[1]
		r.close()
		return int(pid)
		
	#Detect 
	def run(self):

		global SHUTDOWN

		# debug
		# idxFile 생성 
		self.idxFile = self.tfile + ".info"
		#self.idxFile = "./idx.info"
	
		#log별 idx파일이 존재하면 값 받아오고 없으면 0저장
		if os.path.isfile(self.idxFile):
			lineNum = self.LoadIdx()
		else:
			lineNum = 0

		self.lineNum = int(lineNum)


		#파일의 현재까지 읽은 line부터 프로레스를 연다.
		self.rfp = os.popen("tail -n+%s -f %s" %(lineNum, self.tfile))
		#print "tail -n+%s -f %s" %(lineNum, self.tfile)
		#time.sleep(10)
		self.pid = self.GetPid()
		__LOG__.Trace("target file = %s" % tfile)

		#현재 시간을 받아온다.
		self.stime = time.time()
		#파일에 접근했을 때 해당 파일의 사이즈를 받아온다.
		self.csize = os.stat(self.tfile)[stat.ST_SIZE]

		#SHUTDOWN
		while not SHUTDOWN:

			try:time.time()
				#??select를 잉ㅇ하여 
				input, output, ex = select.select([self.rfp], [], [], 1)
			except Exception, err:
				#if err[0] == "I/O operation on closed file":
				__LOG__.Exception()

			
			if input:
				try:
					#data에 rfp로부터 읽은 것을 저장, line 값 하나 증가
					data = self.rfp.readline()
					self.lineNum += 1
					if not data:
						SHUTDOWN = True
						continue
					#parser 호출 , 패턴과 로그를 검사하는 놈 호출
					self.Parser(data)
	
				except:
					__LOG__.Exception()
					SHUTDOWN = True
			#Retail호출 , 기존 log파일이 백업이 이루어 졌는지 체크해서 검사를 계속 이어나가게 함
			self.ReTail()

		#idx값 업데이트
		self.DumpIdx(self.lineNum)

	#ReTail 함수
	def ReTail(self):

		#파일의 존재유무 체크
		if not os.path.isfile(self.tfile):
			__LOG__.Trace("Not found file")
			return
		#새로운 파일 접근 시간 체크
		msize = os.stat(self.tfile)[stat.ST_SIZE]

		#기존 파일과 새로운 파일의 사이즈를 비교 , 이것을 통해 사이즈를 비교해서 새롭게 실행된 파일이 무엇인지 비교
		if int(msize) < int(self.csize):
			#기존 실행되던 프로세스를 죽인다.
			os.kill(self.pid, 15)
			self.rfp.close()
			#해당 파일로 새롭게 프로세스를 오픈한다. 프로세스 값을 받아옴
			self.rfp = os.popen("tail -n+%s -f %s" %(0,self.tfile))
			self.pid = self.GetPid()
			#사이즈 새롭게 업데이트
			self.csize = msize
			__LOG__.Trace("reopen target file = %s" % tfile)

		#사이즈 새로고침 0으로
		if self.TimeCheck():
			self.csize = msize

	
	def TimeCheck(self):

		ctime = time.time()

		# 현재 시간과 시작 시작의 차이가 reload시간보다 크면 true 반환
		if (ctime - self.stime) > int(self.ttime):
			self.stime = ctime
			return True

		return False


	#parser 패턴 비교 후 문자
	def Parser(self, data):

		global SHUTDOWN

		#mtime 시간 변형
		mtime = time.strftime("%H:%M")
		#search 패턴과 데이터 비교
		rst = re.search(self.tprtn, data)
		if rst:
			for conf in self.smsList:
				name, num, telecom = self.config.get("SMS receive list", conf).split("|")
				num = "".join(num.split("-"))
				sms = "[%s] %s '%s' error or exception" % (self.target[:20], mtime, data[:16])
				
				if telecom == 'SKT"':
					#SendMessage(num, sms,self.HOST,self.PORT,self.from_num)
					__LOG__.Trace("%s %s" % (num, sms))
				else:
					pass		
			#SHUTDOWN = True

#메인 함수
if __name__ == '__main__':

	#들어온 값리스트화
	options, args = getopt.getopt(sys.argv[1:], "")
	#args 값 확인
	if len(args) != 1:
		print "Usage: %s [CONFIG FILE]" % sys.argv[0]
		print "       %s ./Server_Log_Mon.ini" % sys.argv[0]
		sys.exit()

	#Server_Log_Mon.ini 저장
	cfg = args[0]
	#configParser 값 호출
	config 	= ConfigParser.ConfigParser()
	config.read(cfg)
	#common 섹션에서 path 값 읽기
	path = config.get("common", "path")
	
	#host/ port/ from_num

	#SMS_info  HOST PORT FROM_NUM.
	HOST = config.get("SMS_info","HOST")
	HOST = str(HOST)
	print(HOST)
	PORT = config.get("SMS_info","PORT")
	PORT = int(PORT)
	print(PORT)
	from_num = config.get("SMS_info","FROM_NUM")
	print(from_num)
	from_num = str(from_num)





	# Logging
	Log.Init()
	#Log.Init(Log.CRotatingLog(path+"/Server_Log_Mon.log", 10000000, 3))
	__LOG__.Trace("***** Startup Process *****")

	thlst = []
	#config.setction 을 차례대로 돌면서
	for target in config.sections():
		if target == "SMS receive list" or target == "common":
			continue
		#config 탐색  Target 섹션에서  tfile : 파일 절대 경로값, tprtn : 찾고자 하는 패턴 , ttime : reload 시간.
		if target.startswith("Target") :
			tfile = config.get(target, "target_file")
			tprtn = config.get(target, "target_data_line_pattern")
			ttime = config.get(target, "file_reload_period")

			#Detect 클래스 호출, thread 생성됨
			obj = Detect(target, config, tfile, tprtn, ttime,HOST,PORT,from_num)
			#데몬thread로 만듬
			obj.setDaemon(True)
			#thread 시작
			obj.start()
    		thlst.append(obj)

	for th in thlst:
		th.join()

	__LOG__.Trace("***** END Process *****")

