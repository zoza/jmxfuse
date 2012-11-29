#!/usr/bin/env python

from distutils.core import setup
   
setup(name='jmxfuse',
      version="0.1",
      description='A JMX Mbeans filesystem',
      author='Alastair McCormack',
      author_email='alastair.mccormack@mcc-net.co.uk',
      url='http://code.google.com/p/jmxfuse/',
      packages=['jmx_fuse'],
      package_dir = {'': 'src'},
      scripts =['scripts/jmxfuse'],
      license = "GNU GPLv3",
      classifiers=['License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)',
                   'Development Status :: 3 - Alpha',
                   'Environment :: Console',
                   'Operating System :: POSIX :: Linux',
                   'Topic :: System :: Filesystems'
                   ]
     )