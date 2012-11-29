"""
    Tree Manager - Holds an in memory tree of the filesystem

    @license: GPL
    @copyright: Alastair McCormack
    @author: Alastair McCormack
    @contact: alastair@mcc-net.co.uk
"""

import logging
import fs
from datetime import datetime, timedelta
import re
import sys

class jmx_tree_manager:
    root_dir = None
    mbean_server = None
    rescan_interval = None
    rescan_timedelta = None
    last_build_time = None
    
    @classmethod
    def init(cls, mbean_server, rescan):
        cls.mbean_server = mbean_server
        cls.set_rescan(rescan)
    
    @classmethod
    def set_rescan(cls, time_r):
        """ Sets rescan interval by time, using prepended m or s to specify seconds or minutes.
            Defaults to seconds if no modifier given
        """
        
        logging.debug("Setting rescan interval to: %s" % time_r)
        time_format_match = re.match("(\d+)\s*([ms]?)", time_r, re.IGNORECASE)
        if time_format_match:
            logging.debug("String matched regex")
            new_rescan = int(time_format_match.group(1))
            logging.debug("new_rescan %s" % new_rescan)
            time_format_mod = time_format_match.group(2)
            logging.debug("time_format_mod: %s" % time_format_mod)
            
            
            if time_format_mod == "m":
                cls.rescan_timedelta = timedelta(minutes = new_rescan)
                cls.rescan_interval = "%sm" % new_rescan
            else:
                cls.rescan_timedelta = timedelta(seconds = new_rescan)
                cls.rescan_interval = "%ss" % new_rescan
                
            logging.debug("Set rescan_timedelta to %s" % cls.rescan_timedelta)
            
    @classmethod
    def rebuild_on_next_request(cls):
        logging.debug("Clearing root_dir ready for rebuild")
        cls.root_dir = None
        logging.debug("Root dir: %s" % cls.root_dir)
    
    @classmethod
    def build_tree(cls):
        # build dir tree
        logging.debug("Building tree")
        cls.root_dir = fs.root_directory()
        
        connection_info_file = fs.file("connection_info")
        connection_info_file.set_contents("%s:%s" % (cls.mbean_server.server, cls.mbean_server.port))       
        cls.root_dir.add_child(connection_info_file)
        
        connection_info_file = fs.file_rescan_interval("rescan")        
        cls.root_dir.add_child(connection_info_file)
        
        try:
            for mbean in cls.mbean_server.get_mbeans():
                mbean_name = mbean.get_name_array()
                parent = cls.root_dir
                
                # Get all but the last elements of the mbean name
                for mbean_name_element in mbean_name[:-1]:
                    #logging.debug("Adding %s to parent %s" % (mbean_name_element, parent.get_name()))
                    new_parent = parent.add_directory(mbean_name_element)
                    parent = new_parent
                # Get the last part of the element name
                mbean_dir = fs.mbean_directory(mbean_name[-1], mbean)
                parent.add_child(mbean_dir)
        except:
            msg = "%s - %s" % sys.exc_info()[0:2]
            logging.error(msg)
            error_file = fs.file("error")
            error_file.set_contents(msg)
            cls.root_dir.add_child(error_file)

            
        cls.last_build_time = datetime.now()
    
    @classmethod
    def __get_depth(cls, path):
        """
        Return the depth of a given path, zero-based from mount point ('/')
        """
        if path == '/':
            return 0
        else:
            return path.count('/')

    @classmethod
    def get_path(cls, path):
        logging.debug("Last build time: %s" % cls.last_build_time)
        logging.debug("Now: %s" % datetime.now())
        logging.debug("Rescan interval: %s" % cls.rescan_interval)
        next_build_time = 0
        if cls.last_build_time:
            next_build_time = cls.last_build_time + cls.rescan_timedelta
            logging.debug("Next build time: %s" % next_build_time)
        # If now > last_time+rescan_interval or root_dir is empty
        logging.debug("Root dir: %s" % cls.root_dir)
        if not cls.root_dir:
            cls.build_tree()
        elif datetime.now() >= next_build_time:
            # Rebuild tree
            logging.debug("Rebuilding tree")
            cls.build_tree()
        
        path_list = path.split("/")[1:]
        logging.debug("Path: %s" % path)
        logging.debug("Path List: %s" % path_list)
        
        dir = None
        
        if cls.__get_depth(path) == 0:
            logging.debug("Root dir")
            dir = cls.root_dir
        else:
            parent = cls.root_dir
            for path_element in path_list:
                # navigate down fs objects
                dir = parent.get_child(path_element)
                parent = dir
        
        return dir