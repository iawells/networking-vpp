# Copyright (c) 2016 Cisco Systems, Inc.
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.


# This is a simple Flask application that provides REST APIs by which
# compute and network services can communicate, plus a REST API for
# debugging using a CLI client.

# Note that it does *NOT* at this point have a persistent database, so
# restarting this process will make Gluon forget about every port it's
# learned, which will not do your system much good (the data is in the
# global 'backends' and 'ports' objects).  This is for simplicity of
# demonstration; we have a second codebase already defined that is
# written to OpenStack endpoint principles and includes its ORM, so
# that work was not repeated here where the aim was to get the APIs
# worked out.  The two codebases will merge in the future.

from flask import Flask
from flask_restful import reqparse, abort, Api, Resource
import os
import logging
import logging.handlers

# Basic log config
logger = logging.getLogger('gluon')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
logger.addHandler(ch)
logger.debug('Debug logging enabled')

# Basic Flask RESTful app setup
app = Flask('vpp-agent')

api = Api(app)

######################################################################

port_parser = reqparse.RequestParser()
port_parser.add_argument('id')

def abort_if_port_doesnt_exist(id, backend=None):
    if id not in ports:
        abort(404, message="Port {} doesn't exist".format(id))
    if backend is not None and ports[id]['backend'] != backend:
        abort(404, message="Port {} doesn't exist".format(id))

def do_backend_bind(backend, port_id, device_owner, zone, device_id,
                    host, binding_profile):
    """Helper function to get a port bound by the backend.

    Once bound, the port is owned by the network service and cannot be
    rebound by that service or any other without unbinding first.

    Binding consists of the compute and network services agreeing a
    drop point; the compute service has previously set binding
    requirements on the port, and at this point says where the port
    must be bound (the host); the network service will work out what
    it can achieve and set information on the port indicating the drop
    point it has chosen.

    Typically there is some prior knowledge on both sides of what
    binding types will be acceptable, so this process could be
    improved.
    """

    logger.debug('Binding port %s on backend %s: compute: %s/%s/%s location %s' 
                 % (port_id, backend['name'], device_owner, 
                    zone, device_id, host))
    driver = backend_manager.get_backend_driver(backend)
    # TODO these are not thoroughly documented or validated and are a
    # part of the API.  Write down what the values must be, must mean
    # and how the backend can use them.
    driver.bind(port_id, 
	device_owner, zone, device_id,
	host, binding_profile)

    # TODO required?  Do we trust the backend to set this?
    ports[port_id]['zone'] = zone

def do_backend_unbind(backend, port_id):
    """Helper function to get a port unbound from the backend.

    Once unbound, the port becomes ownerless and can be bound by
    another service.  When unbound, the compute and network services
    have mutually agreed to stop exchanging packets at their drop
    point.

    """

    driver = backend_manager.get_backend_driver(backend)
    driver.unbind(port_id)

networks = {}
class VPPNetwork(object):
    def __init__(self, id):
	self.id = id
	self.local_ports = {}
	self.port_idx = None
	global networks
	networks[id] = self

    def dataplane_create(self):
	
	# blah

	self.port_idx = port_idx


    def dataplane_delete(self):
	# blah(self.port_idx)

	self.port_idx = None

    def maybe_cleanup(self):
	if self.local_ports == {}:
	    self.dataplane_delete(self)

class VPPPort(object):
    def __init__(self, id, network_id):
	self.id = id
	global networks
	if not networks[network_id]:
	    VPPNetwork(network_id)
	self.network = networks[network_id]
	self.port_idx = None


    def dataplane_create(self):
	self.network.dataplane_create()
	self.network.local_ports[id] = self

	# blah(self.network.port_idx)

    def dataplane_delete(self):
	del self.network.local_ports[id]
	self.network.maybe_delete()

	

class Port(Resource):
    """The resource providing the specific PUT operations to bind and
    unbind a port.

    The previous interface relied on setting of certain properties at
    a given momnt in time to indicate a bind.  We're implementing
    something more like a method for those operations.
    """

    def __init__(self, my_host):
	self.my_host = my_host # Nova's idea of what host we are

	self.ports={}

	self.bind_args = parser = reqparse.RequestParser()
        self.bind_args.add_argument('host')
        self.bind_args.add_argument('device_owner')
        self.bind_args.add_argument('zone')
        self.bind_args.add_argument('device_id')
        self.bind_args.add_argument('pci_profile')
        self.bind_args.add_argument('rxtx_factor')

	self.notify_args = parser = reqparse.RequestParser()
        self.bind_args.add_argument('event')
        self.bind_args.add_argument('device_id')
        self.bind_args.add_argument('device_owner')

    def _bind(self, id):
	args = self.bind_args.parse_args()
	binding_profile={
	    'pci_profile': args['pci_profile'],
	    'rxtx_factor': args['rxtx_factor']
	    # TODO add negotiation here on binding types that are valid
            # (requires work in Nova)
	}
	accepted_binding_type = \
            do_backend_bind(backends[ports[id]['backend']], id,
                            args['device_owner'], args['zone'], 
                            args['device_id'], args['host'],
                            binding_profile)
	# TODO accepted binding type should be returned to the caller

    def _unbind(self, id):
	# Not very distributed-fault-tolerant, but no retries yet
	do_backend_unbind(backends[ports[id]['backend']], id)

    def put(self, id, op):
	# Note: contrary to your expectations, this can be called
	# more than once in bound or unbound state.

	if op == 'bind':
	    self._bind(id)
	elif op == 'unbind':
	    self._unbind(id)
	else:
	    return 'Invalid operation on port', 404

##
## Actually setup the Api resource routing here
##
api.add_resource(Port, '/ports/<id>/<op>')



# TODO port should probably be configurable.
def main():
    app.run(debug=True, port=2704)

if __name__ == '__main__':
    main()
