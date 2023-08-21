from dotenv import dotenv_values
import logging
env = dotenv_values()
level = logging.NOTSET
if env.get('DEBUG') == '1':
    level = logging.DEBUG
logging.basicConfig(format='%(asctime)s %(message)s')
log = logging.getLogger('LexZ')
log.setLevel(level)
