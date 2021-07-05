#!/bin/bash

PWD=`pwd`

# Get version
function GetVersion(){
    if [[ -s /etc/redhat-release ]];then
        grep -oE  "[0-9.]+" /etc/redhat-release
    else
        grep -oE  "[0-9.]+" /etc/issue
    fi
}

# CentOS version
function CentosVersion(){
    local code=$1
    local version="`GetVersion`"
    local main_ver=${version%%.*}
    if [ $main_ver == $code ];then
        return 0
    else
        return 1
    fi
}

check_sys(){
    local checkType=$1
    local value=$2

    local release=''
    local systemPackage=''

    if [[ -f /etc/redhat-release ]]; then
        release='centos'
        systemPackage='yum'
    elif grep -Eqi 'debian|raspbian' /etc/issue; then
        release='debian'
        systemPackage='apt'
    elif grep -Eqi 'ubuntu' /etc/issue; then
        release='ubuntu'
        systemPackage='apt'
    elif grep -Eqi 'centos|red hat|redhat' /etc/issue; then
        release='centos'
        systemPackage='yum'
    elif grep -Eqi 'debian|raspbian' /proc/version; then
        release='debian'
        systemPackage='apt'
    elif grep -Eqi 'ubuntu' /proc/version; then
        release='ubuntu'
        systemPackage='apt'
    elif grep -Eqi 'centos|red hat|redhat' /proc/version; then
        release='centos'
        systemPackage='yum'
    fi

    if [[ "${checkType}" == 'sysRelease' ]]; then
        if [ "${value}" == "${release}" ]; then
            return 0
        else
            return 1
        fi
    elif [[ "${checkType}" == 'packageManager' ]]; then
        if [ "${value}" == "${systemPackage}" ]; then
            return 0
        else
            return 1
        fi
    fi
}

install_check(){
    if check_sys packageManager yum || check_sys packageManager apt; then
        if centosversion 5; then
            return 1
        elif centosversion 6; then
            return 1
        fi
        return 0
    else
        return 1
    fi
}

install_dependencies(){
    if ! install_check; then
        echo -e "[${red}Error${plain}] Your OS is not supported to run it!"
        echo 'Please change to CentOS 7+/Ubuntu 16+ and try again.'
        exit 1
    fi

    clear
    if check_sys packageManager yum;then

        yum_depends=(
            make automake  kernel-devel openssl-devel git wget tar
        )

        for depend in ${yum_depends[@]}; do
            yum install -y ${depend}
        done

        if CentosVersion 8;then
            yum -y install python38 python38-devel gcc gcc-c++ gmp-devel libsodium libsodium-devel libsodium-static
            ln -s /usr/bin/python3.8 /usr/bin/python3
            install_cmake
        else
            install_devtoolset-8-gcc-g++
            yum -y install python3 python3-devel gmp-devel libsodium gmp-static libsodium-static
            install_cmake3.14.5
            install_python38
        fi

    elif check_sys packageManager apt;then

        apt_depends=(
            libsodium-dev libgmp3-dev make automake gcc gcc-c++ g++ build-essential libssl-dev git cmake wget tar libsodium-dev
        )

        for depend in ${apt_depends[@]}; do
            apt install -y ${depend}
        done

        apt install -y python3.8 python3.8-dev python3.8-venv
        ln -s /usr/bin/python3.8 /usr/bin/python3

    fi
    PythonBin="/usr/bin/python3.8"
}

install_chia_plotter(){
    cd ${PWD}
    echo "Starting install chia-plotter"
    git submodule update --init chia-plotter
    cd chia-plotter
    git submodule update --init
    ./make_devel.sh
    install_path=`pwd`
    ln -s -f ${install_path}/build/chia_plot /usr/bin/
    echo "done."
    cd ../
}

install_swar(){
    cd ${PWD}
    echo "Starting install swar"
    $PythonBin -m venv venv
    ln -s ${PWD}/venv/bin/activate ./
    source ./activate
    pip install -r requirements.txt
    pip install -r requirements-notification.txt
    deactivate
    echo "done."
}

install_cmake(){
    current_pwd=`pwd`
    [ -d "/usr/local/cmake" ] && return 0
    [ -d "/tmp/cmake" ] && rm -rf /tmp/cmake
    mkdir -p /tmp/cmake
    cd /tmp/cmake
    wget https://github.com/Kitware/CMake/releases/download/v3.20.2/cmake-3.20.2.tar.gz
    tar -zxvf cmake-3.20.2.tar.gz
    cd cmake-3.20.2
    ./bootstrap --prefix=/usr/local/cmake
    gmake && gmake install
    ln -s -f /usr/local/cmake/bin/cmake /usr/bin/cmake
    cd ${current_pwd}
}

install_cmake3.14.5() {
    current_pwd=`pwd`
    [ -d "/usr/local/cmake" ] && return 0
    [ -d "/tmp/cmake" ] && rm -rf /tmp/cmake
    mkdir -p /tmp/cmake
    cd /tmp/cmake
    wget https://cmake.org/files/v3.14/cmake-3.14.5.tar.gz
    tar -zxvf cmake-3.14.5.tar.gz
    cd cmake-3.14.5
    ./bootstrap --prefix=/usr/local/cmake
    gmake && gmake install
    ln -s -f /usr/local/cmake/bin/cmake /usr/bin/cmake
    cd ${current_pwd}
}

install_devtoolset-8-gcc-g++() {
    yum -y install centos-release-scl
    yum -y install devtoolset-8-gcc*
    [ -f /usr/bin/gcc ] && mv /usr/bin/gcc /usr/bin/gcc-4.8
    [ -f /usr/bin/g++ ] && mv /usr/bin/g++ /usr/bin/g++-4.8
    ln -s /opt/rh/devtoolset-8/root/bin/gcc /usr/bin/gcc
    ln -s /opt/rh/devtoolset-8/root/bin/g++ /usr/bin/g++
    source /opt/rh/devtoolset-8/enable
}

install_python38() {
    current_pwd=`pwd`
    [ -d "/tmp/python3.8" ] && rm -rf /tmp/python3.8
    mkdir /tmp/python3.8
    cd /tmp/python3.8
    wget https://www.python.org/ftp/python/3.8.8/Python-3.8.8.tgz
    tar -zxvf Python-3.8.8.tgz
    cd Python-3.8.8
    ./configure --prefix=/usr/local/python3.8
    make && make install
    ln -s -f /usr/local/python3.8/bin/python3.8 /usr/bin/python3.8
    cd ${current_pwd}
}

clean_tmps() {
    [ -d "/tmp/cmake" ] && rm -rf /tmp/cmake
    [ -d "/tmp/chiapos" ] && rm -rf /tmp/chiapos
    [ -d "/tmp/python3.8" ] && rm -rf /tmp/python3.8
}

install_dependencies
install_swar
install_chia_plotter
clean_tmps
