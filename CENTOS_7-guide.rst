====================
CentOS 7 Setup Guide
====================

This document describes steps to set up a Centos 7 single host devstack 
environmenmt using networking-vpp.

Host Setup
~~~~~~~~~~

 #. Configure hugepage and iommu support:
 
    ``default_hugepagesz=2M hugepagesz=2M hugepages=2048 iommu=pt
    intel_iommu=on``

 #. Configure libvirtd to run qemu as root:
    In file ``/etc/libvirt/qemu.conf``, set user and group to root, and check
    the path of the hugepages

 #. Install etcd and configure etcd::

      yum install -y etcd

    The file ``/etc/etcd/etcd.conf`` should contains::

      ETCD_NAME=default
      ETCD_DATA_DIR="/var/lib/etcd/default.etcd"
      ETCD_LISTEN_CLIENT_URLS="http://localhost:4001"
      ETCD_ADVERTISE_CLIENT_URLS="http://localhost:4001"

 #. Enable etcd::

      systemctl enable etcd
      systemctl start etcd


VPP build and install
~~~~~~~~~~~~~~~~~~~~~

 #. pull VPP source from git::

      git clone https://gerrit.fd.io/r/vpp

 #. Build and install VPP::

      cd vpp
      make install-dep
      make build-release
      make pkg-rpm

 #. Install VPP rpms. The rpms are located in vpp/built-root directory after
    build is complete::

      sudo yum install build-root/vpp*.rpm


 #. Build and install VPP-PAPI. VPP-PAPI is VPP's python API used by
    networking-vpp.

    * Install python-devel package if it is not installed already::

        sudo install -y python-devel

    * Build and install::

        make build-vpp-api
        cd vpp-api/python
        sudo python setup.py install

    * Copy missing files::

        cp ./build-root/install-vpp_debug-native/vpp/vpp-api/vpe.py /usr/lib/python2.7/site-packages/vpp_papi-1.1-py2.7.egg/vpp_papi/
        cp ./build-root/install-vpp_debug-native/vlib-api/vlibmemory/memclnt.py /usr/lib/python2.7/site-packages/vpp_papi-1.1-py2.7.egg/vpp_papi/
        cp ./build-root/build-vpp_debug-native/vpp-api/python/.libs/*.so* /usr/lib/python2.7/site-packages/vpp_papi-1.1-py2.7.egg/vpp_papi/
        replace in file /usr/lib/python2.7/site-packages/vpp_papi-1.1-py2.7.egg/vpp_papi/vpp_papi.py 
            "vpe = sys.modules['vpe']" by "import vpe"

     * Check vpp_papi is correctly installed::

         python
         >> import vpp_papi  <-- should not raise any exception      

 #. Configuring VPP

    It may be desirable to change vpp cli's listening port to something other
    than the default 5000, as it is used by keystone. This can be done by
    adding line ``cli-listen localhost:5002`` in ``unix`` section of VPP
    config file ``/etc/vpp/startup.conf``.
 
    Add a line corresponding to your external NIC in the ``dpdk`` section,
    and limit the amount of memory taken by VPP::

        dpdk {
            socket-mem 1024
            uio-driver uio_pci_generic
            dev 0002:05:00.0
        }

 #. Starting VPP

    VPP can be started by starting VPP service::

      systemctl start vpp

    To verify VPP has started correctly::

      vppctl show interface

    You should see your physical NIC listed in the interface list, in this
    case GigabitEthernet2/5/0::

        Name               Idx       State          Counter          Count
        GigabitEthernet2/5/0              5        down
        local0                            0        down
        pg/stream-0                       1        down
        pg/stream-1                       2        down
        pg/stream-2                       3        down
        pg/stream-3                       4        down


More detailed instruction on vpp building and installing can be found at:
https://wiki.fd.io/view/VPP/Build,_install,_and_test_images#Build_A_VPP_Package

Upgrade qemu-kvm
~~~~~~~~~~~~~~~~

 #. Enable Centos EV repo
 
    ``yum install centos-release-qemu-ev``

 #. Update packages, this will pick up new qemu packages from EV repo.

    ``yum update``

 #. Remove qemu-system-x86 package if it's installed, this will prevent
    libvirt from identifying QEMU version to be 2.0 

    ``yum remove qemu-system-x86``


Build and install qemu
~~~~~~~~~~~~~~~~~~~~~~

If you would like to use qemu rather than qemu-kvm, you can build and 
install qemu with the following steps:

::

  wget http://wiki.qemu-project.org/download/qemu-2.3.1.tar.bz2
  tar xvf qemu-2.3.1.tar.bz2
  cd qemu-2.3.1
  sudo yum install gtk2-devel
  ./configure  --enable-numa
  make
  sudo make install

Devstack Setup
~~~~~~~~~~~~~~

General direction on how to download and set up devstack can be found at http://docs.openstack.org/developer/devstack/

Add the following to local.conf::

  disable_service n-net q-agt
  disable_service cinder c-sch c-api c-vol
  disable_service tempest

  enable_plugin networking-vpp https://github.com/iawells/networking-vpp.git
  ENABLED_SERVICES+=,q-svc,q-meta,q-dhcp
  Q_PLUGIN=ml2
  Q_ML2_TENANT_NETWORK_TYPE=vlan
  ML2_VLAN_RANGES=physnet:100:200
  Q_ML2_PLUGIN_EXT_DRIVERS=
  Q_ML2_PLUGIN_MECHANISM_DRIVERS=vpp
  Q_ML2_PLUGIN_TYPE_DRIVERS=vlan
  VLAN_TRUNK_IF='GigabitEthernet2/5/0'
  MECH_VPP_PHYSNETLIST=physnet:GigabitEthernet2/5/0
  MECH_VPP_AGENTLIST=localhost
  QEMU_USER=root
  QEMU_GROUP=root
  NEUTRON_CREATE_INITIAL_NETWORKS=False
  

Note that ``VLAN_TRUNK_IF`` and ``MECH_VPP_PHYSNETLIST`` should be set to the interface name in VPP that you
want to use as your trunk interface.


Network creation
~~~~~~~~~~~
As the variable ``NEUTRON_CREATE_INITIAL_NETWORKS`` is set to ``False``, we have to create
manually the private network::
  source openrc admin admin
  neutron net-create --tenant-id admin --provider:network_type vlan --provider:physical_network physnet private
  neutron subnet-create --tenant-id admin --name sub_private --gateway 192.168.78.1 --enable-dhcp --ip-version 4 private 192.168.78.0/24


VM creation
~~~~~~~~~~~

Note that hugepage support is required on guest VMs for vhostuser port
attachment, this can be done by creating a new flavor and booting the VM with
the flavor::

  nova flavor-create m1.tiny.hugepage auto 512 0 1
  nova flavor-key m1.tiny.hugepage set  hw:mem_page_size=2048

  nova boot --image cirros-0.3.4-x86_64-uec --flavor m1.tiny.hugepage --nic net-name=private myvm

