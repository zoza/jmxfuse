#!C:\Python26\python.exe
# -*- coding: utf-8 -*-  
"""
    @author: Alastair McCormack
    
"""

import sys
import logging
import optparse
from jmxFuse import core

core_jmx_fuse = core.jmx_fuse()
core_jmx_fuse.parser.add_option(mountopt="host", default="localhost", type="string", help="host - default: %default")
core_jmx_fuse.parser.add_option(mountopt="port", type="int", default=8080, help="port - default: %default")
core_jmx_fuse.parser.add_option(mountopt="rescan", type="string", default="60m", help="Interval between refreshing mbean structure. Append m for minutes and s for seconds -  default: %default")
core_jmx_fuse.parser.add_option(mountopt="encoding", type="string", default="utf-8", help="Filename encoding. default: %default")
core_jmx_fuse.parser.add_option(mountopt="backend", type="string", default="jolokia", help="JMX Access backend - default: %default")
core_jmx_fuse.parse(errex=1)

values = core_jmx_fuse.parser.values 

if hasattr(values, "d"):
    logging_level = logging.DEBUG
else:
    logging_level = logging.ERROR

logging.basicConfig(level=logging_level,format='%(asctime)s %(levelname)s %(name)s %(funcName)s %(message)s')

if not values.host or not values.port:
    try:
        core_jmx_fuse.parser.error("host and port must be given")
    except (optparse.OptParseError):
        sys.exit(1)

core_jmx_fuse.init(host=values.host, port=values.port, rescan=values.rescan,
                   encoding=values.encoding, backend=values.backend)
core_jmx_fuse.main()
