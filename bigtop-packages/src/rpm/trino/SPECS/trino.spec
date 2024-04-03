# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

%define trino_name trino
%define trino_pkg_name trino%{pkg_name_suffix}

%define trino_cli_name trino-cli



%define etc_default %{parent_dir}/etc/default
%define usr_lib_trino %{parent_dir}/usr/lib/%{trino_name}
%define usr_lib_trino_cli %{parent_dir}/usr/lib/%{trino_cli_name}

%define var_lib_trino %{parent_dir}/var/lib/%{trino_name}
%define etc_trino %{parent_dir}/etc/%{trino_name}
%define np_etc_trino /etc/%{trino_name}
%define etc_trino_conf_dist %{parent_dir}/etc/%{trino_name}/conf.dist
%define bin_dir %{parent_dir}/%{_bindir}

%define var_run_trino /var/run/%{trino_name}
%define var_log_trino /var/log/%{trino_name}
%define config_trino /etc/%{trino_name}

%define bin /usr/bin/
%define man_dir /usr/share/man/man1
%define trino_services server
%define trino_current_version 415
%define _binaries_in_noarch_packages_terminate_build   0

%if  %{?suse_version:1}0
%define doc_trino %{_docdir}/trino
%define alternatives_cmd update-alternatives
%else
%define doc_trino %{_docdir}/trino-%{trino_version}
%define alternatives_cmd alternatives
%endif

# disable repacking jars
%define __os_install_post %{nil}
%define __jar_repack %{nil}
%define  debug_package %{nil}


Name: %{trino_pkg_name}
Version: %{trino_version}
Release: %{trino_release}
Summary: Distributed SQL Query Engine for Big Data
URL: https://trinodb.io/
Group: Development/Libraries
BuildArch: noarch
Buildroot: %{_topdir}/INSTALL/%{name}-%{version}
License: ASL 2.0
AutoReqProv: no
Source0: %{trino_name}.tar.gz
Source1: do-component-build
Source2: install_trino.sh
Source3: trino-server.svc
Source4: init.d.tmpl
Source5: bigtop.bom
Source6: trino.conf
Requires: python
Requires(preun): /sbin/service

%define initd_link /etc/rc.d
%global initd_dir %{_sysconfdir}/rc.d/init.d
%global __provides_exclude_from ^%{_javadir}/%{name}/jbr/.*$
%global __requires_exclude_from ^%{_javadir}/%{name}/jbr/.*$

%if  %{?suse_version:1}0 && %{!?mgaversion:1}0 && %{!?amzn2:1}0
# Required for init scripts
Requires: redhat-lsb
%endif

# if amazonlinux2
%if %{?amzn2:1}0
Requires: sh-utils, system-lsb
%define initd_link /etc/rc.d

%else
# Required for init scripts
Requires: /lib/lsb/init-functions
%define initd_link /etc/rc.d

%endif

%description
trino is an open source distributed SQL query engine for running
interactive analytic queries against data sources of all sizes ranging
from gigabytes to petabytes.

%package server
Summary: trino Server
Group: Development/Libraries
BuildArch: noarch
Requires: %{trino_pkg_name} = %{version}-%{release}

%description server
Server for trino

%package cli
Summary: trino CLI
Group: Development/Libraries
BuildArch: noarch
Requires: %{trino_pkg_name} = %{version}-%{release}

%description cli
CLI for trino

%prep
%setup -n %{trino_name}

%build
bash %{SOURCE1}

%install
%__rm -rf $RPM_BUILD_ROOT
%__install -d -m 0755 $RPM_BUILD_ROOT/%{initd_dir}/
bash %{SOURCE2} \
        --cli-build-dir=build/trino-cli \
        --cli-dir=%{usr_lib_trino_cli} \
        --build-dir=build/trino \
        --lib-dir=%{usr_lib_trino}  \
        --var-dir=%{var_lib_trino}  \
        --prefix=${RPM_BUILD_ROOT} \
        --conf-dist-dir=%{etc_trino_conf_dist}

for service in %{trino_services}
do
  # Install init script
  init_file=$RPM_BUILD_ROOT/%{initd_dir}/%{trino_name}-${service}
  bash $RPM_SOURCE_DIR/init.d.tmpl $RPM_SOURCE_DIR/trino-${service}.svc rpm $init_file
done


%pre
getent group trino >/dev/null || groupadd -r trino
getent passwd trino >/dev/null || useradd -c "Trino" -s /sbin/nologin -g trino -r -d %{var_lib} trino 2> /dev/null || :


%post
%{alternatives_cmd} --install %{np_etc_trino}/conf %{trino_name}-conf %{etc_trino}/conf.dist 30

%preun
if [ "$1" = 0 ]; then
        %{alternatives_cmd} --remove %{trino_name}-conf %{etc_trino}/conf.dist || :
fi

for service in %{trino_services}; do
  /sbin/service %{trino_name}-${service} status > /dev/null 2>&1
  if [ $? -eq 0 ]; then
    /sbin/service %{trino_name}-${service} stop > /dev/null 2>&1
  fi
done


%files
%defattr(-,root,root,755)
%attr(0755,root,root) %{usr_lib_trino}
%attr(0755,trino,trino) %config(noreplace) %{np_etc_trino}
%config(noreplace) %{etc_trino}/conf.dist
%attr(0755,trino,trino) %{var_run_trino}
%attr(0755,trino,trino) %{var_log_trino}

%files cli
%{usr_lib_trino_cli}

%define service_macro() \
%files %1 \
%config(noreplace) %{initd_dir}/%{trino_name}-%1 \
%post %1 \
chkconfig --add %{trino_name}-%1 \
%preun %1 \
/sbin/service %{trino_name}-%1 status > /dev/null 2>&1 \
if [ "$?" -eq 0 ]; then \
        service %{trino_name}-%1 stop > /dev/null 2>&1 \
        chkconfig --del %{trino_name}-%1 \
fi \
%postun %1 \
if [ "$?" -ge 1 ]; then \
        service %{trino_name}-%1 condrestart > /dev/null 2>&1 || : \
fi
%service_macro server