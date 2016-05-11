import csv
import Ip_Ch as IP_CHECK


class bgp():

	def __init__(self,csv_data,cfg):
		
		self.ip_addr=[]
		self.cfg=cfg
		self.conf_ip=[]
		self.dict={}

		for ip in csv_data:
			self.ip_addr.append(ip[2])

		
	
	def bgp_run(self):

		for i in self.cfg:
			if i.find('network') != -1 :
				i = list(i.split())
				self.conf_ip.append(i[1])
		len_ip = len(self.conf_ip)
			
		for data in self.ip_addr:
			for i in self.conf_ip:

				if i.find(data) != -1:
					print 'conflict'
					self.dict[i] ='O'
				else:
					self.dict[i] ='X'
		return self.dict	
					
class Result():
	
	def __init__(self,ifRes,bgpRes):
		
		#first
		self.ifRes =ifRes
		self.bgpRes=bgpRes
		print ifRes.keys()[1][1]

	def First(self):
		self.len_n = len(self.ifRes)
		self.arr_list=[]
		self.second=[]
		for i in range(self.len_n):
			if self.ifRes.keys()[i][0] in self.bgpRes.keys():
				self.arr_list.append(self.ifRes.keys()[i][0], self.ifRes.values()[i],self.bgpRes[ifRes.keys()[i][0]], self.ifRes.keys()[i][1])	
		self.len_2=len(self.arr_list)

		for i in range(self.len_2):
			if arr_list[i][1] =="X" or arr_list[i][2]=="X":
				self.second.append(arr_list[i])
		
		
		with open("/root/user/ecycle/first.csv",'w') as first_f:
			for i in self.arr_list:
				first_f.write(i)
                with open("/root/user/ecycle/second.csv",'w') as second_f:
                        for i in self.second:
                                second_f.write(i)
						
				
		

if __name__=="__main__":

	inif = open("/etc/quagga/bgpd.conf",'r')	
	
	cfg=inif.readlines()
	csv_data = csv.reader(file('MBS.csv'))
	

	my_bgp= bgp(csv_data,cfg)
	ip_ch = IP_CHECK.If_Check()
	ifRes= ip_ch.checker()
	bgpRes= my_bgp.bgp_run()
	

	print ifRes
	print bgpRes
	result_f = Result(ifRes,bgpRes)
	print result_f.First()
	
