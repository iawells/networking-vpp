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
from flask_restful import Api
from flask_restful import reqparse
from flask_restful import Resource
import logging
import logging.handlers
import os
import vpp

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

VHOSTUSER_DIR = '/tmp'


class VPPForwarder(object):

    def __init__(self, external_if):
        self.vpp = vpp.VPPInterface()
        self.external_if = external_if

        self.networks = {}      # vlan: bridge index
        self.interfaces = {}    # uuid: if idx

        for (ifname, f) in self.vpp.get_interfaces():
            # Clean up interfaces from previous runs

            # TODO(ijw) can't easily SPOT VLAN subifs to delete

            if ifname.startswith('tap-'):
                self.vpp.delete_tap(f.sw_if_index)
            elif ifname.startswith('VirtualEthernet'):
                self.vpp.delete_vhostuser(f.sw_if_index)

            ext_ifstruct = self.vpp.get_interface(external_if)
            self.ext_ifidx = ext_ifstruct.swifindex

    # This, here, is us creating a VLAN backed network
    def network_on_host(self, vlan):
        if vlan not in self.networks:
            # TODO(ijw): bridge domains have no distinguishing marks.
            # VPP needs to allow us to name or label them so that we
            # can find them when we restart

            # TODO(ijw): this VLAN subinterface may already exist, and
            # may even be in another bridge domain already (see
            # above).
            if_upstream = self.vpp.create_vlan_subif(self.ext_ifidx, vlan)
            self.vpp.ifup(if_upstream)

            br = self.vpp.create_bridge_domain()

            self.vpp.add_to_bridge(br, if_upstream)

            self.networks[vlan] = br

        return self.networks[vlan]

    def create_interface_on_host(self, type, uuid, mac):
        if uuid not in self.interfaces:

            if type == 'tap':
                name = uuid[0:11]
                iface = self.vpp.create_tap(name, mac)
                props = {'vif_type': 'tap', 'name': name}
            elif type == 'vhostuser':
                path = os.path.join(VHOSTUSER_DIR, uuid)
                iface = self.vpp.create_vhostuser(path, mac)
                props = {'vif_type': 'vhostuser', 'path': uuid}
            else:
                raise Exception('unsupported interface type')

            self.interfaces[uuid] = iface

        return (self.interfaces[uuid], props)

    def bind_interface_on_host(self, type, uuid, mac, vlan):
        net_br_idx = self.network_on_host(vlan)

        (iface, props) = self.create_interface_on_host(type, uuid, mac)

        self.vpp.ifup(iface)
        self.vpp.add_to_bridge(net_br_idx, iface)

        return props


######################################################################

bind_args = reqparse.RequestParser()
bind_args.add_argument('mac')
bind_args.add_argument('vlan')
bind_args.add_argument('host')

vppf = VPPForwarder('GigabitEthernet2/2/0')  # TODO(ijw) make config


class PortBind(Resource):

    def put(self, id):
        global vppf

        args = self.bind_args.parse_args()
        vppf.bind_interface_on_host('vhostuser',
                                    id,
                                    args['mac'],
                                    args['vlan'])


class PortUnbind(Resource):

    def __init(self, *args, **kwargs):
        super('PortBind', self).__init__(*args, **kwargs)

    def put(self, id, host):
        pass  # should destroy interface, but doesn't yet


api.add_resource(PortBind, '/ports/<id>/bind')
api.add_resource(PortUnbind, '/ports/<id>/unbind/<host>')


def main():
    # TODO(ijw) port etc. should probably be configurable.
    app.run(debug=True, port=2704)

if __name__ == '__main__':
    main()
