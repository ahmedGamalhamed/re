from datetime import datetime
import coloredlogs, logging

logger = logging.getLogger(__name__)
coloredlogs.install(fmt='[%(asctime)s] %(message)s')

def log(tag, text):
	monitor_time = datetime.now().strftime('%m-%d-%Y %H:%M:%S')
	# Info tag
	with open('logs.txt', 'a+') as f:
		if(tag == 'i'):
			logger.info("[INFO] " + text)
			f.write("[{}] [INFO] {}\n".format(monitor_time, text))
		# Error tag
		elif(tag == 'e'):
			logger.error("[ERROR] " + text)
			f.write("[{}] [ERROR] {}\n".format(monitor_time, text))
		# Success tag
		elif(tag == 's'):
			logger.warning("[SUCESS] " + text)
			f.write("[{}] [SUCESS] {}\n".format(monitor_time, text))
		# Warning tag
		elif(tag == 'w'):
			logger.warning("[WARNING] " + text)
			f.write("[{}] [WARNING] {}\n".format(monitor_time, text))
		# Fail tag
		elif(tag == 'f'):
			logger.critical("[FAIL] " + text)
			f.write("[{}] [FAIL] {}\n".format(monitor_time, text))
