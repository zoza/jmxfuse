'''
    An implementation of a mx4j connector and abstract mbean classes. These mbean
    classes need to be abstracted further so that they can be implemented by other
    connectors

    @license: GPL
    @copyright: Alastair McCormack
    @author: Alastair McCormack
    @contact: alastair@mcc-net.co.uk

'''
import urllib2
import logging
import re

try:
    # Python 2.5 includes Elementree by default
    import xml.etree.ElementTree as ET
except ImportError:
    try:
        # pylint: disable=F0401
        import ElementTree as ET
    except ImportError:
        # pylint: disable=F0401
        import elementtree.ElementTree as ET

class Mx4jparser:
    """ Provides an interface to mx4j's HTTP XML interface """
    __server_name = None
    __port = None
    __protocol = None
    __base_url = None
    
    def __init__(self, server_name, port, protocol="http://"):
        self.__server_name = server_name
        self.__port = port
        self.__protocol = protocol
        self.__base_url = "%s%s:%s" % (self.__protocol, self.__server_name, self.__port)
        
    def get_url(self):
        return self.__base_url
        
    def __get_XML(self, path, queryString=""):
        # If queryString is set and first char in not "?"
        if queryString and queryString[0] != "?":
            queryString = "?" + queryString
        
        if queryString:
            query_url = "/%s%s" % (path, queryString)
        else:
            query_url = "/%s" % path
        
        url = self.get_url() + query_url
        logging.debug("Getting url: " + url)
        return urllib2.urlopen(url)
    
    def get_ET(self, path, queryString=""):
        serverXML = self.__get_XML(path, queryString)
        return ET.parse(serverXML)
    
    def get_server_xml(self):
        path = "server"
        serverXML = self.__get_XML(path)
        serverbydomainET = ET.parse(serverXML)
        return serverbydomainET
    
    def get_serverbydomain_xml(self):
        path = "serverbydomain"
        serverXML = self.__get_XML(path)
        serverbydomainET = ET.parse(serverXML)
        domains = serverbydomainET.findall("//Domain")
        return domains
    
    def get_mbean_xml(self, mbean_object_name):
        path = "mbean"
        query = "objectname=%s" % mbean_object_name
        mbean_xml = self.get_ET(path, query).getroot()
        return mbean_xml
    
    def get_mbean_attribute_xml(self, mbean_object_name, attribute):
        path = "getattribute"
        query = "objectname=%s&attribute=%s" % (mbean_object_name, attribute)
        attribute_xml    = self.get_ET(path, query).find("Attribute")
        return attribute_xml
    
    def set_mbean_attribute_xml(self, mbean_object_name, attribute, value):
        path = "setattribute"
        query = "objectname=%s&attribute=%s&value=%s" % (mbean_object_name, attribute, value)
        attribute_xml = self.get_ET(path, query).find("Attribute")
        return attribute_xml
        
    def get_domain_names(self, domain_name_filter=None):
        query = None
        if domain_name_filter:
            query = "querynames=%s:*" % domain_name_filter
                
        path = "serverbydomain"
        serverXML = self.__get_XML(path, query)
        
        serverbydomainET = ET.parse(serverXML)
        domains = serverbydomainET.findall("//Domain")
        for domain in domains:
            yield domain.get("name")
            
    def get_mbean_classnames(self, domain):
        """
            Get unique mbean class names for domain path
        """
        
        results_list = []
        
        query = "querynames=%s:*" % domain
        path = "serverbydomain"
        serverXML = self.__get_XML(path, query)
        serverbydomainET = ET.parse(serverXML)
        mbeans = serverbydomainET.findall("//MBean")
        
        for mbean in mbeans:
            class_name = mbean.get("classname")
            print class_name
            if class_name not in results_list:
                print "Adding classname:" + class_name
                results_list.append(class_name)
        return results_list
            
    def invoke_mbean_operation(self, mbean_object_name, operation_name, mbean_operation_parameters):
        """
            Invoke operation
            @mbean_operation_parameters is a list of mbean_operation_paramaters
        """
        query = "objectname=%s&operation=%s" % (mbean_object_name, operation_name)
        path = "invoke"
    
        if mbean_operation_parameters:
            param_query_list = []
            
            for mop in mbean_operation_parameters:
                type = mop.get_type()
                id = mop.get_id()
                value = mop.get_request_value();
                param_query_list.append("type%s=%s" % (id, type))
                param_query_list.append("value%s=%s" % (id, value))
                
            query += "&" + "&".join(param_query_list)
        
        operation_xml = self.get_ET(path, query).find("Operation")
        return operation_xml


class mbean:
    """ A JMX mbean """
    name = None
    server = None
    attributes = None
    operations = None
    mbean_xml = None
    null = False
    
    def __init__(self, name, server):
        self.name = name
        self.server = server
        self.attributes = []
        self.operations = []
                
    def get_xml_attribute(self, attribute_name):
        return self.get_mbean_xml().get(attribute_name)
    
    def get_class_name(self):
        return self.get_xml_attribute("classname")
    
    def get_description(self):
        return self.get_xml_attribute("description")
    
    def get_object_name(self):
        return self.get_xml_attribute("objectname")
    
    def get_attributes(self):
        attributes_elements = self.get_mbean_xml().findall("Attribute")
        for attribute_element in attributes_elements:
            attribute_name = attribute_element.get("name")
            availability = attribute_element.get("availability")
            yield mbean_attribute(attribute_name, self, availability)
            
    def get_operations(self):
        ops = []
        operation_elements = self.get_mbean_xml().findall("Operation")
        for operation_element in operation_elements:
            operation_name = operation_element.get("name")
            ops.append( mbean_operation(operation_name, operation_element, self) )
        return ops
        
    def get_server(self):
        return self.server
    
    def get_mbean_xml(self):
        """Get mbean xml element"""
        if not self.mbean_xml:
            server = self.get_server()
            http_parser = server.get_http_parser()
            self.mbean_xml = http_parser.get_mbean_xml(self.name)                
        return self.mbean_xml
    
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
             

class mbean_attribute:
    availability = None
    name = None
    mbean = None
    read = False
    write = False

    def __init__(self, name, mbean, availability="RW"):
        self.mbean = mbean
        
        #mbean_xml = self.mbean.get_mbean_xml()
        self.name = name
        
        if "R" in availability:
            self.read = True
        if "W" in availability:
            self.write = True
        
    def get_name(self):
        return self.name
    
    def __parse_tabular_data(self, value):
        """ Parses data returned from javax.management.openmbean.TabularData """
        jmp = java_map_processor(value)
        return jmp.format()
        
    def get_value(self):
        """ Fetches attribute xml and returns value """
        http_parser = self.mbean.get_server().get_http_parser()
        attribute_xml = http_parser.get_mbean_attribute_xml(self.mbean.get_object_name(), self.name)
        logging.debug("Attribute_xml: %s" % attribute_xml)
        attribute_isnull = attribute_xml.get("isnull")
        value = attribute_xml.get("value")
        
        logging.debug("Value is: %s" % value)
        
        if value.startswith("javax.management.openmbean.TabularDataSupport"):
            value = self.__parse_tabular_data(value)
            
        if attribute_isnull == "true":
            return None
        else:
            return value
        
    def set_attribute(self, value):
        http_parser = self.mbean.get_server().get_http_parser()
        attribute_xml = http_parser.set_mbean_attribute_xml(self.mbean.get_object_name(), self.name, value)
        return attribute_xml
    
class mbean_operation:
    name = None
    mbean = None
    parameters = None
    operation_xml = None
    return_type = None
    
    def __init__(self, name, operation_xml, mbean):
        self.name = name
        self.mbean = mbean
        self.operation_xml = operation_xml
        
        self.return_value_type = self.operation_xml.get("return")
        self.description = self.operation_xml.get("description")
            
    def get_paramters(self):
        parameter_elements = self.operation_xml.findall("Parameter")
        result = []
        if parameter_elements:
            for parameter_element in parameter_elements:
                name = parameter_element.get("name")
                type = parameter_element.get("type")
                description = parameter_element.get("description")
                id = int(parameter_element.get("id"))   
                result.append(mbean_operation_parameter(id=id, type=type, mbean_operation=self, name=name, description=description))
        
        # Sorts list according to id
        result.sort(key=mbean_operation_parameter.get_id)
        return result
            
    def invoke(self, parameters=None):
        http_parser = self.mbean.get_server().get_http_parser()
        result_xml = http_parser.invoke_mbean_operation(self.mbean.get_object_name(), self.name, parameters)
        return mbean_operation_invoke_result(result_xml)
        
    def get_mbean(self):
        return self.mbean
    
    def get_return_type(self):
        return self.return_type
    
    def get_name(self):
        return self.name
    
    def get_description(self):
        return self.description
    
class mbean_operation_invoke_result:
    """ The result from an mbean operation """
    def __init__(self, result_xml):
        self.result_xml = result_xml
        
    def get_result(self):
        return self.result_xml.get("result")
    
    def get_error_msg(self):
        return self.result_xml.get("errorMsg")
    
    def __str__(self):
        return self.get_result()
        
class mbean_operation_parameter:
    """ An mbean operation parameter/arguments """ 
    id = None
    type = None
    name = None
    description = None
    mbean_operation = None
    request_value = None
    
    def __init__(self, id, type, mbean_operation, name=None, description=None):
        self.id = id
        self.type = type
        self.mbean_operation = mbean_operation
        self.name = name
        self.description = description
        
    def get_id(self):
        return self.id
    
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

class server:
    """ Represents a connection to a JMX RMI Servers"""
    
    jmx_http_parser = None
    directories = {}
    server = None
    port = None
    
    def __init__(self, server, port):
        self.server = server
        self.port = port
        self.jmx_http_parser = Mx4jparser(server, port)
        
    def get_mbeans(self):
        mbeans_xml = self.get_server_xml().findall("MBean")
        for mbean_xml in mbeans_xml:
            mbean_name = mbean_xml.get("objectname")
            yield mbean(mbean_name, self)
            
    def get_http_parser(self):
        return self.jmx_http_parser
    
    def get_server_xml(self):
        server_xml = self.get_http_parser().get_server_xml()
        return server_xml
    
class java_map_processor:
    """ Decodes Java Map Objects returned in XML """
    map_string = None
    
    def __init__(self, map_string):
        self.map_string = map_string
        
    def format(self, indent=0):
        result = ""
        indent_str = ""
        for i in xrange(indent): #@UnusedVariable
            indent_str = "  "
            
            
        braces = self.get_braces()
        for brace in braces:
            key_pair = self.parse_key_value(brace)
            if key_pair:
                result += "%s%s=%s\n" % (indent_str, key_pair[0], key_pair[1])
            jmp = java_map_processor(brace)
            new_indent = indent + 1
            result += jmp.format(new_indent)
        return result
                
    def parse_key_value(self, string):
        key_pair_re = re.compile("^key=(.+?),\svalue=(.*)")
        
        matches = key_pair_re.finditer(string)
        
        for match in matches:
            return (match.group(1), match.group(2))
         
    def get_braces(self):
        brace_depth = 0
        content = ""
        
        for s in self.map_string:
            if s == "{":
                # new open brace
                brace_depth += 1    
            elif s == "}":
                brace_depth -= 1
            elif content and brace_depth == 0:
                # end of brace found
                yield content.strip("{}")
                content = ""
            if brace_depth:
                content += s

