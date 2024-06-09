import sys
import os
import subprocess

def get_gateway():
	with open(os.devnull, 'w') as devnull:
		output = subprocess.check_output(["cmd","/c","chcp","437","&","tracert","-d","-h","1","1.1.1.1","&","chcp","866"], stderr=devnull)
	try:
		decode = output.decode("cp437")
	except:
		print ("Ошибка декодирования")
		return
		
	line4 = decode.split("\r\n")[4].strip().split(" ")
	for data in line4:
		if len(data.split(".")) == 4:
			return(data)		
	return

def get_ip_address():
	print("")
	ip_address='192.168.1.1'
	if not ip_address:
		print("Шлюз не найден")
		sys.exit(1)

	print("Шлюз по умолчанию: {ip_address}".format(ip_address=ip_address))
	print("")
	return ip_address
