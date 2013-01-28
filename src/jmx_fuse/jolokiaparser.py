'''
    An implementation of a Jolokia connector and abstract mbean classes. These mbean
    classes need to be abstracted further so that they can be implemented by other
    connectors

    @license: GPL3
    @copyright: Alastair McCormack
    @author: Alastair McCormack
    @contact: alastair@mcc-net.co.uk

'''

import logging
import requests
import re
import json

MBEAN_ACL_READ = 4
MBEAN_ACL_WRITE = 2

class NullHandler(logging.Handler):
    def emit(self, record):
        pass
    
log = logging.getLogger(__name__)
log.addHandler(NullHandler())


def get_json(response):
        """ Early versions of requests library do not include built-in json support """
        unicode_text = response.text
        return json.loads(unicode_text)
    

class Mbean_Attribute_Write_Exception(Exception):
    pass

class Mbean_Operation_Exec_Exception(Exception):
    pass

class Mbean_Server_Exception(Exception):
    pass

class mbean:
    """ A JMX mbean """

    def __init__(self, name, server):
        self.name = name
        self.server = server
        self.attributes = []
        self.operations = []
        
    def get_server(self):
        return self.server
    
    def get_name_array(self):
        """ Returns a name array similar to the hierarchy found in jconsole """ 
        
        # self.name will be similar to "java.lang:type=GarbageCollector,name=PS MarkSweep"
        # Depth 0 will return java.lang
        # Depth 1 will return GarbageCollector
        # Depth 2 will return PS MarkSweep
        result = []
        
        # Get and add "domain" section (part before ":")
        colon_split_array = self.name.split(":")
        result.append( colon_split_array[0] )
        
        remainder_array = colon_split_array[1].split(",")
        for name_pair in remainder_array:
            # Get value of key/val pair
            value = name_pair.split("=")[1]
            value = value.strip("/")
            # If quoted return string whole without quotes
            if value.startswith('"') and value.endswith('"'):
                result.append(value.strip('"'))
            else:
                # Further split string by "/" if string is NOT quoted
                # If no slashed exist .split() will return the string
                for slash_ele in value.split("/"):
                    result.append(slash_ele)
        return result
            
        
    def get_name(self, depth=False):
        if not depth:
            return self.name
        else:
            return self.get_name_array()[depth]
    
    def get_path_name(self):
        name_array = self.get_name_array()
        path = "/" + "/".join(name_array)
        return path
    
    def get_object_name(self):
        return self.name
    
    def get_class_name(self):
        return None
    
    def get_description(self):
        return None
    
    def get_attributes(self):
        raise NotImplementedError()
               
    def get_operations(self):
        raise NotImplementedError()

class Jolokia_mbean(mbean):
    
    def get_class_name(self):
        return None
    
    def get_description(self):
        return None
    
    def get_attributes(self):
        return self.server.get_mbean_attributes(self)
               
    def get_operations(self):
        return self.server.get_mbean_operations(self)
        
class mbean_attribute:
    
    def __init__(self, name, mbean, read=True, write=False):
        self.mbean = mbean
        self.name = name
        
        self.read = read
        self.write = write
        
    def get_name(self):
        return self.name
    
class Jolokia_mbean_attribute(mbean_attribute):
            
    def get_value(self):
        return self.mbean.server.get_mbean_attribute_value(self.name, self.mbean)
        
    def set_attribute(self, value):
        return self.mbean.server.set_mbean_attribute_value(self.name, value, self.mbean)
    
class mbean_operation(object):

    def __init__(self, name, mbean, return_type, description, params):
        self.name = name
        self.mbean = mbean               
        self.return_type = return_type
        self.description = description
        self.params = params
    
    def get_mbean(self):
        return self.mbean
    
    def get_return_type(self):
        return self.return_type
    
    def get_name(self):
        return self.name
    
    def get_description(self):
        return self.description

    def invoke(self, parameters=None):
        raise NotImplementedError()
    
    def get_paramters(self):
        return self.params

class Jolokia_mbean_operation(mbean_operation):
              
    def invoke(self, parameters=None):
        return self.mbean.server.invoke_mbean_operation(self.mbean, self.name, parameters)
        
class mbean_operation_parameter(object):
    """ An mbean operation parameter/arguments """ 
    
    def __init__(self, param_type, mbean_operation, name=None, description=None):
        self.type = param_type
        self.mbean_operation = mbean_operation
        self.name = name
        self.description = description
            
    def get_type(self):
        return self.type
    
    def get_name(self):
        return self.name
    
    def get_description(self):
        return self.description
    
    def set_request_value(self, value):
        self.request_value = value
        
    def get_request_value(self):
        return self.request_value

class mserver(object):
    """ Represents a connection to a JMX Servers"""
    
    def __init__(self, server, port):
        self.server = server
        self.port = port
        self.directories = {}
        
    def get_mbeans(self):
        raise NotImplementedError()
    
    def test(self):
        """Tests connectivity. Raises exception on error"""
        raise Mbean_Server_Exception(NotImplementedError())

class Jolokia_server(mserver):
    
    def __init__(self, server, port):
        mserver.__init__(self, server, port)
        self.url = "http://%s:%s/jolokia" % (self.server, self.port)
        
        self.test()
        
    def get_mbeans(self):
        r = requests.get("%s/list?maxDepth=2" % self.url)
        json = get_json(r)
        for (top_level_name, sub_names) in json["value"].items():
            for sub_name in sub_names:
                mbean_name = "%s:%s" % (top_level_name, sub_name)
                yield Jolokia_mbean(mbean_name, self)
                
    def _split_mbean_name(self, mbean):
        """ Split mbean domain from name and returns parts as tuples"""
        mbean_dom_re = re.compile("^(.*?):(.*)")
        mbean_composite_name = mbean.name
        mb_name_match = mbean_dom_re.search(mbean_composite_name)
        return ( mb_name_match.group(1), mb_name_match.group(2) )
    
    def _escape_mbean_name(self, mbean_name):
        return mbean_name.replace("!", "!!").replace("/", "!/")
    
    def get_mbean_attributes(self, mbean):
        """Get mbean_attributes of mbean"""
        (mbean_domain, mbean_name) = self._split_mbean_name(mbean)
        r = requests.get("%s/list/%s/%s/attr" % (self.url, self._escape_mbean_name(mbean_domain), self._escape_mbean_name(mbean_name)))
        
        rjson = get_json(r)
        for (attribute_name, attribute_details) in rjson["value"].items():
            writable = attribute_details["rw"]
            yield Jolokia_mbean_attribute(attribute_name, mbean, read=True, write=writable)
            
    def get_mbean_attribute_value(self, name, mbean):
        mbean_name = mbean.name
        r = requests.get("%s/read/%s/%s" % (self.url, self._escape_mbean_name(mbean_name), name))
        value = get_json(r)["value"]
        # If value is a list or a dictionary then Jolokia has kindly deserialised the value.
        # We will simple return it as a line fed string
        if isinstance(value, (dict,list)):
            return value.__str__()
        else:
            return value
        
    def get_mbean_operations(self, mbean):
        def get_params_from_args(arg_list):
            result = []
            for arg in arg_list:
                param = mbean_operation_parameter(arg["type"], arg["name"], arg["desc"])
                result.append(param)
            return result
        
        (mbean_domain, mbean_name) = self._split_mbean_name(mbean)
        r = requests.get("%s/list/%s/%s/op" % (self.url, self._escape_mbean_name(mbean_domain),
                                               self._escape_mbean_name(mbean_name)) )
        
        rjson = get_json(r)
        for (op_name, op_item) in rjson["value"].items():
            
            if isinstance(op_item, dict):
                # Just one signature        
                params = get_params_from_args(op_item["args"])
                yield Jolokia_mbean_operation(op_name, mbean, op_item["ret"], op_item["desc"], params)
                    
            elif isinstance(op_item, list):
                # multiple arg signatures
                for signature in op_item:
                    params = get_params_from_args(signature["args"])
                    yield Jolokia_mbean_operation(op_name, mbean, signature["ret"], signature["desc"], params)
            
         
    def set_mbean_attribute_value(self, name, value, mbean):
        # TODO, change arg order to match invoke_ops 
        value = value.strip()
        post_data = { "type": "write", "attribute":name, "value": value, "mbean": mbean.name}
        post_data_json = json.dumps(post_data)
        log.debug(post_data_json)
        
        r = requests.post(self.url, post_data_json)
        
        result_json = get_json(r)
        if result_json.has_key("error"):
            raise Mbean_Attribute_Write_Exception(result_json["error"])
        return r
    
    def invoke_mbean_operation(self, mbean, op_name, params):
        sig_args = [] 
        args = []
        if params:
            for param in params:
                sig_args.append(param.get_type() )
                args.append(param.get_request_value)
            
        operation = "%s(%s)" % (op_name, ",".join(sig_args))
        
        request_obj = {"type": "EXEC", 
                       "mbean": mbean.name,
                       "operation": operation,
                       "arguments": args
                       }
        
        post_data_json = json.dumps(request_obj)
        log.debug(post_data_json)
        
        r = requests.post(self.url, post_data_json)       
        result_json = get_json(r)
        
        if result_json.has_key("error"):
            raise Mbean_Operation_Exec_Exception(result_json["error"])
        
        if result_json.has_key("value"):
            log.debug("Value: %s" % result_json["value"])
            return result_json["value"]
    
    def test(self):
        # Test connection
        r = requests.get("%s" % self.url)
        try:
            r.raise_for_status()
        except Exception, e:
            raise Mbean_Server_Exception( e )
        
        if get_json(r)["status"] != 200:
            message = r.text
            if "error" in get_json(r):
                message = get_json(r)["error"]
                
            raise Mbean_Server_Exception( message )
        return True