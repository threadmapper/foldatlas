# This is called via Apache/foldatlas.conf, which also sets the python path used by the imports

import logging
import sys

logging.basicConfig( stream=sys.stderr )

print( 'Python version: ' + sys.version )

# now do the import
from app import app as application
