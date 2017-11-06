# The Apache/foldatlas.conf sets the python path so that the daemon knows

import logging
import sys

logging.basicConfig(stream=sys.stderr)

#sys.path.insert(0, '/var/www/foldatlas/foldatlas')

print( 'Python version: ' + sys.version )

# now do the import
from app import app as application
