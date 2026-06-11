#/usr/bin/env python

 'superping.py -- Ping multiple hosts/ipaddresses in parallel.'

  import re
  import threading
  from subprocess import Popen, PIPE 

   # Globals
   COUNT = 2
   TIMEOUT = 1

    class Host(object):
      """
              Defines a host object. Current attributes include: name,
                  address and status.
                      """
                          def __init__ (self, ip):
                            self.ip = ip

                                     def pingHosts(hosts):
                                       """
                                               Creates and starts pinging threads. Displays results upon
                                                   completion.
                                                       Parameters: A list of host objects.
                                                           """
                                                               threads = []
                                                                   nloops = range(len(hosts))

                                                                        # Create Threads
                                                                            for i in nloops:
                                                                              t = threading.Thread(target=execute, args=[hosts[i]])
                                                                                              threads.append(t)

                                                                                                   # Start Threads
                                                                                                       for i in nloops:
                                                                                                         threads[i].start()

                                                                                                                      # Wait for them to finish
                                                                                                                          for i in nloops:
                                                                                                                            threads[i].join()

                                                                                                                                         # Display the results
                                                                                                                                             printResults(hosts)

                                                                                                                                              def execute(host):
                                                                                                                                                """
                                                                                                                                                        Executes a ping command and sets the appropriate attribute.
                                                                                                                                                            Parameters: A host object.
                                                                                                                                                                """
                                                                                                                                                                    f = Popen(('ping -n %s -w %s -a %s' %(COUNT, TIMEOUT, host.ip)),
                                                                                                                                                                        stdout=PIPE).stdout
                                                                                                                                                                    output = f.readlines()
                                                                                                                                                                            f.close()

                                                                                                                                                                                 # Abort if the name is invalid.
                                                                                                                                                                                     if (len(output) == 1):
                                                                                                                                                                                       host.name = 'Not Found'
                                                                                                                                                                                                       host.status = 'Down'
                                                                                                                                                                                                               return

                                                                                                                                                                                                             # Get the host name.
                                                                                                                                                                                                                     pattern = '.+s(.+)s[.+'
                                                                                                                                                                                                                         m = re.search(pattern, output[1])

                                                                                                                                                                                                                              if m is not None:
                                                                                                                                                                                                                                host.name = m.group(1)
                                                                                                                                                                                                                              else:
                                                                                                                                                                                                                                host.name = 'Not Found'

                                                                                                                                                                                                                                                           # Get the status. Take the second reply.
                                                                                                                                                                                                                                                               m = re.search('Reply.+', output[COUNT+1])

                                                                                                                                                                                                                                                                    if m is not None:
                                                                                                                                                                                                                                                                      host.status = 'Alive'
                                                                                                                                                                                                                                                                    else:
                                                                                                                                                                                                                                                                      host.status = 'Down'

                                                                                                                                                                                                                                                                                             def printResults(hosts):
                                                                                                                                                                                                                                                                                               """
                                                                                                                                                                                                                                                                                                       Prints a results: address  status  hostname
                                                                                                                                                                                                                                                                                                           Parameters: A list of host objects
                                                                                                                                                                                                                                                                                                               """
                                                                                                                                                                                                                                                                                                                   print
                                                                                                                                                                                                                                                                                                                       for host in hosts:
                                                                                                                                                                                                                                                                                                                         print "%st%st%s" % (host.ip, host.status, host.name)

                                                                                                                                                                                                                                                                                                                                  if __name__ == '__main__':
                                                                                                                                                                                                                                                                                                                                    """
                                                                                                                                                                                                                                                                                                                                            Main method.
                                                                                                                                                                                                                                                                                                                                                """
                                                                                                                                                                                                                                                                                                                                                    hosts = []

                                                                                                                                                                                                                                                                                                                                                         # A list of addresses. Ideally, these will come from a config file.
                                                                                                                                                                                                                                                                                                                                                             addresses = ['yahoo.com', 'google.com', '1.1.1.0',
                                                                                                                                                                                                                                                                                                                                                                 '10.3.0.1', '10.3.0.2', '10.0.0.3']

                                                                                                                                                                                                                                                                                                                                                             # Create an object for each address
                                                                                                                                                                                                                                                                                                                                                                     for i in range(len(addresses)):
                                                                                                                                                                                                                                                                                                                                                                       hosts.append(Host(addresses[i]))

                                                                                                                                                                                                                                                                                                                                                                                    # Ping them.
                                                                                                                                                                                                                                                                                                                                                                                        pingHosts(hosts)
