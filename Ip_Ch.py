import ConfigParser
import sys
import stat
import os
import subprocess
import csv


class If_Check:
	def getIp_ifname(self):
		ipnDic = {}
		command = 'ip addr | grep "inet "'
		r = subprocess.Popen(command, shell = True ,stdout = subprocess.PIPE)
		for i in r.stdout:
			ifIp = i.split(" ")
			ipnDic[ifIp[len(ifIp)-1].strip('\n')] = ifIp[5].split('/')[0]
		
		
		return ipnDic


	def getCsv(self):
		csvList = []
	
		f = open('./MBS.csv','r')
		csvReader = csv.reader(f)
		
		for i in csvReader:
			csvList.append(i[2])
		f.close()
	
		return csvList

	def checker(self):
		csvList = self.getCsv()
		ipnDic = self.getIp_ifname()
	
		count =0
		dict2={}
		for i in ipnDic.keys():
			if ipnDic[i] in csvList:
				dict2[ipnDic[i], i] = "X"
			else:
				dict2[ipnDic[i],i] = "O"
		
		return dict2			


if __name__ =='__main__':
	
	sta = If_Check()
	print sta.Checker()
