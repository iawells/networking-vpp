sh.# plugin - DevStack plugin.sh dispatch script for vpp

vpp_debug() {
    if [ ! -z "$VPP_DEVSTACK_DEBUG" ] ; then
	"$@" || true # a debug command failing is not a failure
    fi
}

# For debugging purposes, highlight vpp sections
vpp_debug tput setab 1

name=mech_vpp

GITREPO[$name]=${VPP_REPO:-https://github.com/iawells/mech_vpp.git}
GITBRANCH[$name]=${VPP_BRANCH:-master}
GITDIR[$name]="$MECH_VPP_DIR"


# The VPP control plan service (we don't at this point start VPP itself TODO)
if is_service_enabled $cp_service_name; then

    cp_service_name=vpp-cp

    function pre_install_vpp_cp {
	:
    }

    function install_vpp_cp {
	git_clone_by_name $name
	setup_develop ${GITDIR[$name]}
    }

    function init_vpp_cp {
	run_process $cp_service_name "$VPP_CP_BINARY"
    }

    function configure_vpp_cp {
	:
    }

    function shut_vpp_cp_down {
	stop_process $cp_service_name
    }


    if [[ "$1" == "stack" && "$2" == "pre-install" ]]; then
        # Set up system services
        echo_summary "Configuring system services $name"
	pre_install_vpp_cp

    elif [[ "$1" == "stack" && "$2" == "install" ]]; then
        # Perform installation of service source
        echo_summary "Installing $name"
        install_vpp_cp

    elif [[ "$1" == "stack" && "$2" == "post-config" ]]; then
        # Configure after the other layer 1 and 2 services have been configured
        echo_summary "Configuring $name"
        configure_vpp_cp

    elif [[ "$1" == "stack" && "$2" == "extra" ]]; then
        # Initialize and start the service
        echo_summary "Initializing $name"
        init_vpp_cp
    fi

    if [[ "$1" == "unstack" ]]; then
        # Shut down services
	shut_vpp_cp_down
    fi

    if [[ "$1" == "clean" ]]; then
        # Remove state and transient data
        # Remember clean.sh first calls unstack.sh
        # no-op
        :
    fi
fi

vpp_debug tput setab 9
