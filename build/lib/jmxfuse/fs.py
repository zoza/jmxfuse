"""
    A set of classes which map Fuse operations to mbean operations
    
    @license: GPL
    @copyright: Alastair McCormack
    @author: Alastair McCormack
    @contact: alastair@mcc-net.co.uk

"""

import sys
import stat
import time
import types
import logging
from StringIO import StringIO
import httplib
import traceback
import re
import fuse #@UnresolvedImport
import errno
from datetime import datetime
import tm

class FS_Object(object):
    path = None
    mode = 0440
    size = 0
    #children = None
    links = 1
        
    def __init__(self, path):
        self.path = path
        self.children = {}
        self.atime = int(time.time())
        self.mtime = self.atime
        self.ctime = self.atime
    
    def get_fuse_stat(self):
        st = fuse.Stat()    
        st.st_nlink = self.links
        st.st_mode = self.get_type() | self.get_mode()
        st.st_atime = self.atime
        st.st_mtime = self.mtime
        st.st_ctime = self.ctime
        st.st_size = self.get_size()
        return st
        
    def get_mode(self):
        return self.mode
    
    def set_mode(self, mode):
        self.mode = mode
        
    def get_name(self):
        return self.path
        
    def get_child(self, relative_path_name):
        if relative_path_name in self.children:
            return self.children.get(relative_path_name)
        else:
            return None
    
    def get_children(self):
        logging.debug("Children: " + ",".join( self.children.keys() ) )
        print self.children.values()
        return self.children.values()
    
    def get_path(self):
        logging.debug("FSObject: Path: " + self.path)
        return self.path
    
#    def get_direntry(self):
#        return fuse.Direntry( self.get_path().encode("utf-8") )
    
    def get_size(self):
        """ Get size. If self.size is None then calculate size """
        if self.size is not None:
            return self.size
        else:
            return len(self.get_contents())
    
    def set_size(self, size_bytes):
        self.size = size_bytes
    
    def get_type(self):
        return self.fs_type
    
    def __str__(self):
        return self.get_path()
    
class directory(FS_Object):
    fs_type = stat.S_IFDIR
    
    def __init__(self, path):
        super(directory, self).__init__(path)
        self.children["."] = stub_directory(".")
        self.children[".."] = stub_directory("..")
        
    def add_directory(self, child_name):
        if child_name not in self.children:
            logging.debug("Adding child %s" % child_name)
            self.children[child_name] = directory(child_name)
        else:
            logging.debug("Child %s already exists" % child_name)
        return self.children[child_name]
    
    def add_child(self, child):
        self.children[child.get_path()] = child
        
class stub_directory(FS_Object):
    fs_type = stat.S_IFDIR
    
class root_directory(directory):
    fs_type = stat.S_IFDIR
    
    def __init__(self):
        path = ""
        super(root_directory, self).__init__(path)
            
class file(FS_Object):
    contents = ""
    fs_type = stat.S_IFREG
    # File size will be dynamically generated.
    size = None
         
    def get_contents(self):
        # self.contents can be a method to execute first
        if type(self.contents) is types.MethodType:
            return str(self.contents()) + "\n"
        else:
            return str(self.contents) + "\n"
    
    def set_contents(self, contents):
        self.contents = contents
        
    def append_contents(self, contents):
        self.contents += contents
        
    def read(self, path, length, offset, fh=None):
        sio_contents = StringIO(self.get_contents())
        sio_contents.seek(offset)
        return sio_contents.read(length)
            
class mbean_directory(directory):
    """ A class to represent the root of an mbean """
    mbean = None
    
    def __init__(self, path, mbean):
        self.mbean = mbean
        super(mbean_directory, self).__init__(path)
        error_file_contents = ""
        
        try:
            classname_file = file("classname")
            classname_file.set_contents(self.mbean.get_class_name() )
            
            description_file = file("description")
            description_file.set_contents(self.mbean.get_description() )
            
            object_name_file = file("objectname")
            object_name_file.set_contents(self.mbean.get_object_name() )
            
            attributes_dir = mbean_attributes_directory("attributes", self.mbean)
            self.add_child(attributes_dir)
            
            if self.mbean.get_operations():
                ops_dir = mbean_operations_directory("operations", self.mbean)
                self.add_child(ops_dir)
            
            self.add_child(classname_file)
            self.add_child(description_file)
            self.add_child(object_name_file)
        except httplib.BadStatusLine:
                error_file_contents += "Bad Status from Server. Possible bad mbean\n%s\n" % sys.exc_info()[1]  
        except Exception:
                error_file_contents += traceback.format_exc()
                
                
        if error_file_contents:
                logging.warning(error_file_contents)
                error_file = file("error")
                error_file.set_contents(error_file_contents)
                error_file.set_size(None)
                self.add_child(error_file)
                                
class mbean_attributes_directory(directory):
        mbean = None
        
        def __init__(self, path, mbean):
            super(mbean_attributes_directory, self).__init__(path)
            self.mbean = mbean
            for mbean_attr in self.mbean.get_attributes():
                logging.debug("Create attribute file for attribute: %s" % mbean_attr.get_name() )
                new_attribute_file = mbean_attribute(mbean_attr.get_name(), mbean_attr)
                self.add_child(new_attribute_file)
                
#        def opendir(self):
#            # The directory has been opened for reading during an ls
#            # Set children not to return real sizes
#            for child in self.get_children():
#                if isinstance(child, mbean_attribute):
#                    child.set_real_size_false()
#                
#        def releasedir(self):
#            for child in self.get_children():
#                if isinstance(child, mbean_attribute):
#                    child.set_real_size_true()
                
class mbean_operations_directory(directory):
        mbean = None
        
        def __init__(self, path, mbean):
            super(mbean_operations_directory, self).__init__(path)
            self.mbean = mbean
            for mbean_op in self.mbean.get_operations():
                logging.debug("Create operation file for operation: %s" % mbean_op.get_name() )
                new_method_dir = mbean_operation_method_directory(mbean_op.get_name(), mbean_op)
                self.add_child(new_method_dir)
                
class mbean_operation_method_directory(directory):
    mbean_operation = None
    
    def __init__(self, path, mbean_op):
        super(mbean_operation_method_directory, self).__init__(path)
        self.mbean_operation = mbean_op
        
        new_invoke_file = mbean_operation_invoke_file("invoke", self)
        self.add_child(new_invoke_file)
        
        new_usage_file = mbean_operation_usage_file("usage", self)
        self.add_child(new_usage_file)
        
        method_description = self.mbean_operation.get_description()
        if method_description:
            description_file = file("description")
            description_file.set_contents(method_description)
            # Return proper size acording to contents
            description_file.set_size(None)
            
            self.add_child(description_file)    
        
    def write_to_error_file(self, message):
        error_file = self.get_child("error")
        if not error_file:
            error_file = file("error")
            self.add_child(error_file)
        error_file.append_contents(message)
        
    def write_to_results_file(self, message):
        results_file = self.get_child("results")
        if not results_file:
            results_file = file("results")
            self.add_child(results_file)
        results_file.append_contents(message)
        
class mbean_operation_usage_file(file):
    mode = 0440
    # Size will be calculated on the fly
    size = None
    
    def __init__(self, path, mbean_op_method_dir):
        super(mbean_operation_usage_file, self).__init__(path)
        self.mbean_op_method_dir = mbean_op_method_dir
        self.mbean_operation = self.mbean_op_method_dir.mbean_operation
        
        self.parameters = self.mbean_operation.get_paramters()
        self.__set_header()
        
    def __set_header(self):
        args_string = ""
        mbean_name = self.mbean_operation.get_mbean().get_name()
        
        if self.parameters:
            for param in self.parameters:                
                arg_name = '%s' % param.get_name().replace(" ", "_")
                args_string += "%s " % arg_name
        
        self.contents = """Mbean: %s
Operation: %s
Description: %s
Return Type: %s

Usage: echo %s[identifier] > invoke

""" % (mbean_name, self.mbean_operation.get_name(), self.mbean_operation.get_description(), self.mbean_operation.get_return_type(), args_string)

        self.contents += """Arguments:\n"""    
        if self.parameters:
            for param in self.parameters:
                arg_name = '%s' % param.get_name().replace(" ", "_")                
                self.contents += "\t%s\t(%s)\t%s\n" % (arg_name, param.get_type(), param.get_description() )
                
            self.contents += """\tidentifier\t\t\tAn identifier which will appended to each line of the result (Optional)
            
Arguments may be split by space, tab or carriage return
"""
        
class mbean_operation_invoke_file(file):
    """ The invoke file which is used to execute an mbean op.
        It contains a simple usage information """
    # Size will be calculated on the fly
    size = None
           
    mbean_operation = None
    parameters = None
    mbean_op_method_dir = None
        
    def __init__(self, path, mbean_op_method_dir):
        super(mbean_operation_invoke_file, self).__init__(path)
        self.mbean_op_method_dir = mbean_op_method_dir
        self.mbean_operation = self.mbean_op_method_dir.mbean_operation
        
        self.parameters = self.mbean_operation.get_paramters()

        self.mode = 0220 | self.mode
        
    def get_contents(self):
        args_string = ""
        
        if self.parameters:
            for param in self.parameters:
                if param.get_name():
                    arg_name = '%s' % param.get_name().replace(" ", "_")
                else:
                    arg_name =  "arg%s" % param.get_id()
                args_string += "%s " % arg_name
        
        return args_string.strip() + "\n"
        
    def write(self, buf, offset):
        logging.debug("New value: %s" % buf)
        logging.debug("offset: %s" % offset)
        
        dt = datetime.now()
        
        timestamp = dt.isoformat()
        unique_id = ""
        
        if self.parameters:
            no_req_params = len(self.parameters)
        else:
            no_req_params = 0
            
        logging.debug("Number of required args %s" % no_req_params)
        
        value_fh = StringIO(buf)
        value_fh.seek(offset)
        
        value = value_fh.getvalue().strip()
        args = re.split("\s", value)
        
        logging.debug("Number of supplied args: %s" % len(args))
        logging.debug(args)
        
        if len(args) < no_req_params:
            logging.error("Not enough arguments")
            self.mbean_op_method_dir.write_to_error_file("%s Invalid usage. Not enough arguments %s\n" % (timestamp, value))
            return - errno.EINVAL
        
        if len(args) > no_req_params + 1:
            logging.error("Too many arguments")
            self.mbean_op_method_dir.write_to_error_file("%s Invalid usage. Too many arguments: %s\n" % (timestamp, value))
            return - errno.EINVAL
        
        if len(args) == no_req_params + 1:
            unique_id = args.pop()
            
        if args:
            for arg_pos in xrange(len(args)):
                parameter = self.parameters[arg_pos]
                parameter.set_request_value(args[arg_pos])
                
            result = self.mbean_operation.invoke(self.parameters)
        else:
            result = self.mbean_operation.invoke()
        
        results_error = result.get_error_msg()
        results_text = result.get_result()
        
        if results_error:
            message_text = "%s %s" % (results_error, results_text)
        else:
            message_text = results_text
    
        results_message = "%s %s: %s\n" % (timestamp, unique_id, message_text)
        self.mbean_op_method_dir.write_to_results_file(results_message)
            
        return len(buf)
            

class mbean_attribute(file):
    attribute = None
    value = None
    size = 1048576
    
    def __init__(self, attribute_name, attribute):
        super(mbean_attribute, self).__init__(attribute_name)
        self.attribute = attribute
        self.real_size = True
        
        if self.attribute.read:
            self.mode = 0440
            
        if self.attribute.write:
            self.mode = 0220 | self.mode
            
    def get_contents(self):
        result = self.attribute.get_value()
        if result is None:
            result = ""
        return str(result) + "\n"
            
#    def get_value(self):
##        if not self.value:
##            self.value = self.attribute.get_value() + "\n"
##        return self.value
#        return self.attribute.get_value() + "\n"
        
#    def read(self, path, length, offset, fh=None):
#        # self.value could be None from attribute
#        if self.get_value():
#            sio_contents = StringIO(self.get_value())
#        else:
#            sio_contents = StringIO("")
#            
#        sio_contents.seek(offset)
#        return sio_contents.read(length)
    
    def write(self, buf, offset):
        logging.debug("New value: %s" % buf)
        logging.debug("offset: %s" % offset)
        value_fh = StringIO(buf)
        value_fh.seek(offset)
        try:
            self.attribute.set_attribute(value_fh.getvalue())
        except Exception, e:
            logging.debug(e)
            return errno.EIO
        return len(buf)
    
class file_rescan_interval(file):
    mode = 0660
    
    def __init__(self, path):
        super(file_rescan_interval, self).__init__(path)
        
    def get_contents(self):
        return str(tm.jmx_tree_manager.rescan_interval) + "\n"
    
    def truncate(self, size):
        logging.debug("Truncate size: %s" % size)
        sio_contents = StringIO(self.get_contents())
        sio_contents.truncate(size)
        self.write(sio_contents.getvalue())
        return 0
    
    def write(self, buf, offset=0):
        logging.debug("New value: %s" % buf)
        logging.debug("offset: %s" % offset)
        
        value_fh = StringIO(buf)
        value_fh.seek(offset)
        
        match_re = re.match("(\w+)", value_fh.getvalue() )
                
        if not match_re:
            logging.debug("Requesting rebuild on next get_path")
            tm.jmx_tree_manager.rebuild_on_next_request()
        else:
            logging.debug("Setting rescan interval to %s" % match_re.group(0))
            tm.jmx_tree_manager.set_rescan( match_re.group(0) )
        return len(buf)
    