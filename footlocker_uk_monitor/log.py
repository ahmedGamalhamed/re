from datetime import datetime
import coloredlogs, logging

logger = logging.getLogger(__name__)
coloredlogs.install(fmt='[%(asctime)s] %(message)s')

def log(tag, text):
	# Info tag
	if(tag == 'i'):
		logger.info("[INFO] " + text)
	# Error tag
	elif(tag == 'e'):
		logger.error("[ERROR] " + text)
	# Success tag
	elif(tag == 's'):
		logger.warning("[SUCESS] " + text)
	# Warning tag
	elif(tag == 'w'):
		logger.warning("[WARNING] " + text)
	# Fail tag
	elif(tag == 'f'):
		logger.critical("[FAIL] " + text)