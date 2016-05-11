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

	

bind_args = reqparse.RequestParser()
bind_args.add_argument('host')
bind_args.add_argument('device_owner')
bind_args.add_argument('zone')
bind_args.add_argument('device_id')
bind_args.add_argument('pci_profile')
bind_args.add_argument('rxtx_factor')

class PortBind(Resource):

    def put(self, id):
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


class PortUnbind(Resource):

    def __init(*args, **kwargs):
	super('PortBind', self).__init__(*args, **kwargs)

    def put(self, id, host):
	# Not very distributed-fault-tolerant, but no retries yet
	do_backend_unbind(backends[ports[id]['backend']], id)


##
## Actually setup the Api resource routing here
##
api.add_resource(PortBind, '/ports/<id>/bind')
api.add_resource(PortUnbind, '/ports/<id>/unbind/<host>')



# TODO port should probably be configurable.
def main():
    app.run(debug=True, port=2704)

if __name__ == '__main__':
    main()
