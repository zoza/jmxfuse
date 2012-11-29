#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    Expose JMX MBeans as a Fuse Filesystem
    
    @license: GPL
    @copyright: Alastair McCormack
    @author: Alastair McCormack
    @contact: alastair@mcc-net.co.uk
"""

import errno  
import fuse  #@UnresolvedImport - no fuse on Windows :(
import logging
import tm
import jolokiaparser
import sys
  
fuse.fuse_python_api = (0, 2)
        
class jmx_fuse(fuse.Fuse):
    """The main Fuse core. Implemented filesystem operation are defined here"""
    
    def __init__(self, *args, **kw):  
        fuse.Fuse.__init__(self, *args, **kw)
    
    def init(self, host, port, rescan="60m", encoding="utf-8", backend="jolokia", *args, **kw):  
        self.host = host
        self.port = port
        self.rescan = rescan
        self.encoding = encoding
        self.backend = backend
        
        mbean_server = self.backend(self.host, self.port)
        tm.jmx_tree_manager.init(mbean_server, self.rescan)
        
    def test(self):
        self.backend.test()
    
    @property
    def backend(self):
        return self._backend

    @backend.setter
    def backend(self, backend_name):
        # TODO: Find all backend plugins available
        # For now it is just hard coded
        self._backend = jolokiaparser.Jolokia_server
    
#    def fsinit(self): 
#        pass     
   
    def getattr(self, path):
        logging.debug("Path: " + path)
        fs_dir = tm.jmx_tree_manager.get_path(path)
        
        if not fs_dir:
            logging.debug("No such file: %s" % path)
            return -errno.ENOENT

        result = fs_dir.get_fuse_stat()
        
        # Add runtime uid and gid
        result.st_uid = self.GetContext()["uid"]
        result.st_gid = self.GetContext()["gid"]
        
        logging.debug("Size: %s" % result.st_size)
        return result
        
    def readdir(self, path, offset):
        logging.debug("Path: %s" % path)
        fs_dir = tm.jmx_tree_manager.get_path(path)
        
        if not fs_dir:
            logging.debug("No such file: %s" % path)
            yield -errno.ENOENT
        
        for child_dir in fs_dir.get_children():
            logging.debug("Returning Child dir: %s" % child_dir.get_name() )
            yield  fuse.Direntry(child_dir.get_path().encode(self.encoding))
        
#    def open(self, path, flags):  
#        # Only support for 'READ ONLY' flag  
#        access_flags = os.O_RDONLY | os.O_WRONLY | os.O_RDWR  
#        if flags & access_flags != os.O_RDONLY:  
#            return -errno.EACCES  
#        else:  
#            return 0  
        
    def read(self, path, length, offset, fh=None):
        logging.debug("Path: %s" % path)
        logging.debug("Read size: %s" % length)
        logging.debug("Read offset: %s" % offset)
        logging.debug("File Handle: %s" % fh)
        
        fs_file = tm.jmx_tree_manager.get_path(path)
        if not fs_file:
            logging.debug("No such file: %s" % path)
            return -errno.ENOENT
        
        return fs_file.read(path, length, offset, fh).encode(self.encoding)
    
    def write(self, path, buf, offset):
        fs_file = tm.jmx_tree_manager.get_path(path)
        
        if not fs_file:
            logging.debug("No such file: %s" % path)
            return -errno.ENOENT
        elif not hasattr(fs_file, "write"):
            logging.debug("Not implemented")
            return -errno.ENOSYS
        
        logging.debug("Writing to path: %s : %s" % (path, buf))
        return fs_file.write(buf.decode(self.encoding), offset)
        
    def chmod ( self, path, mode ):
        logging.debug( "Path: %s" % path )
        logging.debug("Mode: %s" % mode)
        
    def chown ( self, path, uid, gid ):
        logging.debug("Path: %s" % path )
        logging.debug("uid: %s" % uid)
        logging.debug("gid: %s" % gid)

    def utime ( self, path, times ):
        logging.debug("Path: %s" % path )
        logging.debug("Times: %s" % str(times) )
        
    def truncate ( self, path, size ):
        logging.debug("Path: %s" % path )
        logging.debug("Truncate Size: %s" % size )
        
        fs_file = tm.jmx_tree_manager.get_path(path)
        
        if not fs_file:
            logging.debug("No such file: %s" % path)
            return -errno.ENOENT
        elif not hasattr(fs_file, "truncate"):
            logging.debug("Not implemented")
            return 0
        return fs_file.truncate(size)
        
    def flush(self, path, fh=None):
        return 0
    
#    def opendir(self, path):
#        logging.debug("Opening dir: %s" % path)
#        fs_file = tm.jmx_tree_manager.get_path(path)
#        
#        if not fs_file:
#            logging.debug("No such file: %s" % path)
#            return -errno.ENOENT
#        elif not hasattr(fs_file, "opendir"):
#            logging.debug("Not implemented")
#            return 0
#
#        return fs_file.opendir()

#    def releasedir(self, path):
#        logging.debug("Releasing dir: %s" % path)
#        fs_file = tm.jmx_tree_manager.get_path(path)
#        
#        if not fs_file:
#            logging.debug("No such file: %s" % path)
#            return -errno.ENOENT
#        elif not hasattr(fs_file, "releasedir"):
#            logging.debug("Not implemented")
#            return 0
#
#        return fs_file.releasedir()
    
#    def open(self, path, flags):
#        logging.debug("Opening file: %s" % path)
#        logging.debug("ino: %s" % flags)
#        logging.debug("Flags: %s" % flags)
#        
#        fs_file = tm.jmx_tree_manager.get_path(path)
#        if not fs_file:
#            logging.debug("No such file: %s" % path)
#            return -errno.ENOENT
#        elif not hasattr(fs_file, "open"):
#            logging.debug("Not implemented")
#            return 0
#
#        result = fs_file.open(flags)
#        logging.debug("Open result: %s" % result)
#        return result
#
#    def release(self, path, ino):
#        logging.debug("releaseing file: %s" % path)
#        logging.debug("ino: %s" % ino)
#        
#        fs_file = tm.jmx_tree_manager.get_path(path)
#        if not fs_file:
#            logging.debug("No such file: %s" % path)
#            return -errno.ENOENT
#        elif not hasattr(fs_file, "release"):
#            logging.debug("Not implemented")
#            return 0
#
#        result = fs_file.release(ino)
#        logging.debug("Release result: %s" % result)
#        return result
