# Copyright 2025 Wong Hoi Sing Edison <hswong3i@pantarei-design.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

%global debug_package %{nil}

%global source_date_epoch_from_changelog 0

Name: python-wcmatch
Epoch: 100
Version: 10.0
Release: 1%{?dist}
BuildArch: noarch
Summary: Wilcard File Name matching library
License: MIT
URL: https://github.com/facelessuser/wcmatch/tags
Source0: %{name}_%{version}.orig.tar.gz
BuildRequires: fdupes
BuildRequires: python-rpm-macros
BuildRequires: python3-devel
BuildRequires: python3-setuptools

%description
Wildcard Match provides an enhanced fnmatch, glob, and pathlib library
in order to provide file matching and globbing that more closely follows
the features found in Bash. In some ways these libraries are similar to
Python's builtin libraries as they provide a similar interface to match,
filter, and glob the file system. But they also include a number of
features found in Bash's globbing such as backslash escaping, brace
expansion, extended glob pattern groups, etc. They also add a number of
new useful functions as well, such as globmatch which functions like
fnmatch, but for paths.

%prep
%autosetup -T -c -n %{name}_%{version}-%{release}
tar -zx -f %{S:0} --strip-components=1 -C .

%build
%py3_build

%install
%py3_install
find %{buildroot}%{python3_sitelib} -type f -name '*.pyc' -exec rm -rf {} \;
fdupes -qnrps %{buildroot}%{python3_sitelib}

%check

%if 0%{?suse_version} > 1500
%package -n python%{python3_version_nodots}-wcmatch
Summary: Wilcard File Name matching library
Requires: python3
Requires: python3-bracex >= 2.1.1
Provides: python3-wcmatch = %{epoch}:%{version}-%{release}
Provides: python3dist(wcmatch) = %{epoch}:%{version}-%{release}
Provides: python%{python3_version}-wcmatch = %{epoch}:%{version}-%{release}
Provides: python%{python3_version}dist(wcmatch) = %{epoch}:%{version}-%{release}
Provides: python%{python3_version_nodots}-wcmatch = %{epoch}:%{version}-%{release}
Provides: python%{python3_version_nodots}dist(wcmatch) = %{epoch}:%{version}-%{release}

%description -n python%{python3_version_nodots}-wcmatch
Wildcard Match provides an enhanced fnmatch, glob, and pathlib library
in order to provide file matching and globbing that more closely follows
the features found in Bash. In some ways these libraries are similar to
Python's builtin libraries as they provide a similar interface to match,
filter, and glob the file system. But they also include a number of
features found in Bash's globbing such as backslash escaping, brace
expansion, extended glob pattern groups, etc. They also add a number of
new useful functions as well, such as globmatch which functions like
fnmatch, but for paths.

%files -n python%{python3_version_nodots}-wcmatch
%license LICENSE.md
%{python3_sitelib}/*
%endif

%if !(0%{?suse_version} > 1500)
%package -n python3-wcmatch
Summary: Wilcard File Name matching library
Requires: python3
Requires: python3-bracex >= 2.1.1
Provides: python3-wcmatch = %{epoch}:%{version}-%{release}
Provides: python3dist(wcmatch) = %{epoch}:%{version}-%{release}
Provides: python%{python3_version}-wcmatch = %{epoch}:%{version}-%{release}
Provides: python%{python3_version}dist(wcmatch) = %{epoch}:%{version}-%{release}
Provides: python%{python3_version_nodots}-wcmatch = %{epoch}:%{version}-%{release}
Provides: python%{python3_version_nodots}dist(wcmatch) = %{epoch}:%{version}-%{release}

%description -n python3-wcmatch
Wildcard Match provides an enhanced fnmatch, glob, and pathlib library
in order to provide file matching and globbing that more closely follows
the features found in Bash. In some ways these libraries are similar to
Python's builtin libraries as they provide a similar interface to match,
filter, and glob the file system. But they also include a number of
features found in Bash's globbing such as backslash escaping, brace
expansion, extended glob pattern groups, etc. They also add a number of
new useful functions as well, such as globmatch which functions like
fnmatch, but for paths.

%files -n python3-wcmatch
%license LICENSE.md
%{python3_sitelib}/*
%endif

%changelog
