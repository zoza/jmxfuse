jmxfuse is a python-fuse filesystem which exposes Mbeans attributes and Operations as file objects right from the shell. Read attributes using `cat` and invoke methods using `vi`. You could call it "proc for JMX"!

It relies on the brilliant [Jolokia](http://www.jolokia.org/) to be installed on the target Java server.

# Usage #

## Connect ##
```
# mount a psuedo filesystem
$ jmxfuse -p <jolokia http port no> jmxmnt
```

## List JMX domain ##
```
$ cd jmxmnt
$ ls
Catalina  com.sun.management  connection_info  Http  java.lang  java.util.logging  JMImplementation  jmx4perl  jolokia  log4j  rescan
```

## Attributes ##

### Read ###
```
$ cd log4j/root/attributes
$ cat priority
```

### Write ###
```
$ echo "WARN" >> priority
```

## Operations ##

## Get Description ##

```
$ cd ~/jmxfuse
$ cd Catalina/none/none/WebModule/localhost/helloworld/operations/addParameter
$ cat description
```

### Get usage ###
```
$ cat usage
Mbean: Catalina:J2EEApplication=none,J2EEServer=none,j2eeType=WebModule,name=//localhost/helloworld
Operation: addParameter
Description: Add a new context initialization parameter, replacing any existing value for the specified name.
Return Type: void

Usage: echo Name_of_the_new_parameter Value_of_the_new__parameter [jmxfuseid:identifier] > invoke

Arguments:
        Name_of_the_new_parameter       (java.lang.String)      None
        Value_of_the_new__parameter     (java.lang.String)      None
        identifier                      An identifier which will appended to each line of the result (Optional)

Arguments may be split by space, tab or carriage return
```

### Invoke ###
```
$ echo "myParam myValue" > invoke
$ cat results
```
or
```
$ vi invoke
myParam myValue
<ESC>:wq
```

# Requirements #

  * Fuse
  * Python-fuse

# Installation #

## Jmxfuse ##

  1. `tar zxvf jmxfuse-<version>.tar.gz`
  1. `python setup.py install`

## Jolokia ##

### J2EE ###

  1. Download WAR-Agent from http://www.jolokia.org/download.html

#### General ####

  1. Install WAR file in J2EE Application Server as /jolokia

#### Tomcat ####

  1. Rename war file to `jolokia.war` and drop into webapps directory.