# Copyright 2021 The Pigweed Authors
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.
"""Finds components for a given manifest."""


import pathlib
import sys
import xml.etree.ElementTree


def _element_is_compatible_with_device_core(
    element: xml.etree.ElementTree.Element, device_core: str | None
) -> bool:
    """Check whether element is compatible with the given core.

    Args:
        element: element to check.
        device_core: name of core to filter sources for.

    Returns:
        True if element can be used, False otherwise.
    """
    if device_core is None:
        return True

    value = element.attrib.get('device_cores', None)
    if value is None:
        return True

    device_cores = value.split()
    return device_core in device_cores


def get_component(
    root: xml.etree.ElementTree.Element,
    component_id: str,
    device_core: str | None = None,
) -> tuple[xml.etree.ElementTree.Element | None, pathlib.Path | None]:
    """Parse <component> manifest stanza.

    Schema:
        <component id="{component_id}" package_base_path="component"
                   device_cores="{device_core}...">
        </component>

    Args:
        root: root of element tree.
        component_id: id of component to return.
        device_core: name of core to filter sources for.

    Returns:
        (element, base_path) for the component, or (None, None).
    """
    xpath = f'./components/component[@id="{component_id}"]'
    component = root.find(xpath)
    if component is None or not _element_is_compatible_with_device_core(
        component, device_core
    ):
        return (None, None)

    try:
        base_path = pathlib.Path(component.attrib['package_base_path'])
        return (component, base_path)
    except KeyError:
        return (component, None)


def parse_defines(
    root: xml.etree.ElementTree.Element,
    component_id: str,
    device_core: str | None = None,
) -> list[str]:
    """Parse pre-processor definitions for a component.

    Schema:
        <defines>
          <define name="EXAMPLE" value="1" device_cores="{device_core}..."/>
          <define name="OTHER" device_cores="{device_core}..."/>
        </defines>

    Args:
        root: root of element tree.
        component_id: id of component to return.
        device_core: name of core to filter sources for.

    Returns:
        list of str NAME=VALUE or NAME for the component.
    """
    xpath = f'./components/component[@id="{component_id}"]/defines/define'
    return list(
        _parse_define(define)
        for define in root.findall(xpath)
        if _element_is_compatible_with_device_core(define, device_core)
    )


def _parse_define(define: xml.etree.ElementTree.Element) -> str:
    """Parse <define> manifest stanza.

    Schema:
        <define name="EXAMPLE" value="1"/>
        <define name="OTHER"/>

    Args:
        define: XML Element for <define>.

    Returns:
        str with a value NAME=VALUE or NAME.
    """
    name = define.attrib['name']
    value = define.attrib.get('value', None)
    if value is None:
        return name

    return f'{name}={value}'


def parse_include_paths(
    root: xml.etree.ElementTree.Element,
    component_id: str,
    device_core: str | None = None,
) -> list[pathlib.Path]:
    """Parse include directories for a component.

    Schema:
        <component id="{component_id}" package_base_path="component">
          <include_paths>
            <include_path relative_path="./" type="c_include"
                          device_cores="{device_core}..."/>
          </include_paths>
        </component>

    Args:
        root: root of element tree.
        component_id: id of component to return.
        device_core: name of core to filter sources for.

    Returns:
        list of include directories for the component.
    """
    (component, base_path) = get_component(root, component_id)
    if component is None:
        return []

    include_paths: list[pathlib.Path] = []
    for include_type in ('c_include', 'asm_include'):
        include_xpath = f'./include_paths/include_path[@type="{include_type}"]'

        include_paths.extend(
            _parse_include_path(include_path, base_path)
            for include_path in component.findall(include_xpath)
            if _element_is_compatible_with_device_core(
                include_path, device_core
            )
        )
    return include_paths


def _parse_include_path(
    include_path: xml.etree.ElementTree.Element,
    base_path: pathlib.Path | None,
) -> pathlib.Path:
    """Parse <include_path> manifest stanza.

    Schema:
        <include_path relative_path="./" type="c_include"/>

    Args:
        include_path: XML Element for <input_path>.
        base_path: prefix for paths.

    Returns:
        Path, prefixed with `base_path`.
    """
    path = pathlib.Path(include_path.attrib['relative_path'])
    if base_path is None:
        return path
    return base_path / path


def parse_headers(
    root: xml.etree.ElementTree.Element,
    component_id: str,
    device_core: str | None = None,
) -> list[pathlib.Path]:
    """Parse header files for a component.

    Schema:
        <component id="{component_id}" package_base_path="component">
          <source relative_path="./" type="c_include"
                  device_cores="{device_core}...">
            <files mask="example.h"/>
          </source>
        </component>

    Args:
        root: root of element tree.
        component_id: id of component to return.
        device_core: name of core to filter sources for.

    Returns:
        list of header files for the component.
    """
    return _parse_sources(
        root, component_id, 'c_include', device_core=device_core
    )


def parse_sources(
    root: xml.etree.ElementTree.Element,
    component_id: str,
    device_core: str | None = None,
) -> list[pathlib.Path]:
    """Parse source files for a component.

    Schema:
        <component id="{component_id}" package_base_path="component">
          <source relative_path="./" type="src" device_cores="{device_core}...">
            <files mask="example.cc"/>
          </source>
        </component>

    Args:
        root: root of element tree.
        component_id: id of component to return.
        device_core: name of core to filter sources for.

    Returns:
        list of source files for the component.
    """
    source_files = []
    for source_type in ('src', 'src_c', 'src_cpp', 'asm_include'):
        source_files.extend(
            _parse_sources(
                root, component_id, source_type, device_core=device_core
            )
        )
    return source_files


def parse_libs(
    root: xml.etree.ElementTree.Element,
    component_id: str,
    device_core: str | None = None,
) -> list[pathlib.Path]:
    """Parse pre-compiled libraries for a component.

    Schema:
        <component id="{component_id}" package_base_path="component">
          <source relative_path="./" type="lib" device_cores="{device_core}...">
            <files mask="example.a"/>
          </source>
        </component>

    Args:
        root: root of element tree.
        component_id: id of component to return.
        device_core: name of core to filter sources for.

    Returns:
        list of pre-compiler libraries for the component.
    """
    return _parse_sources(root, component_id, 'lib', device_core=device_core)


def _parse_sources(
    root: xml.etree.ElementTree.Element,
    component_id: str,
    source_type: str,
    device_core: str | None = None,
) -> list[pathlib.Path]:
    """Parse <source> manifest stanza.

    Schema:
        <component id="{component_id}" package_base_path="component">
          <source relative_path="./" type="{source_type}"
                  device_cores="{device_core}...">
            <files mask="example.h"/>
          </source>
        </component>

    Args:
        root: root of element tree.
        component_id: id of component to return.
        source_type: type of source to search for.
        device_core: name of core to filter sources for.

    Returns:
        list of source files for the component.
    """
    (component, base_path) = get_component(root, component_id)
    if component is None:
        return []

    sources: list[pathlib.Path] = []
    source_xpath = f'./source[@type="{source_type}"]'
    for source in component.findall(source_xpath):
        if not _element_is_compatible_with_device_core(source, device_core):
            continue

        relative_path = pathlib.Path(source.attrib['relative_path'])
        if base_path is not None:
            relative_path = base_path / relative_path

        sources.extend(
            relative_path / files.attrib['mask']
            for files in source.findall('./files')
        )
    return sources


def parse_dependencies(
    root: xml.etree.ElementTree.Element, component_id: str
) -> list[str]:
    """Parse the list of dependencies for a component.

    Optional dependencies are ignored for parsing since they have to be
    included explicitly.

    Schema:
        <dependencies>
          <all>
            <component_dependency value="component"/>
            <component_dependency value="component"/>
            <any_of>
              <component_dependency value="component"/>
              <component_dependency value="component"/>
            </any_of>
          </all>
        </dependencies>

    Args:
        root: root of element tree.
        component_id: id of component to return.

    Returns:
        list of component id dependencies of the component.
    """
    dependencies = []
    xpath = f'./components/component[@id="{component_id}"]/dependencies/*'
    for dependency in root.findall(xpath):
        dependencies.extend(_parse_dependency(dependency))
    return dependencies


def _parse_dependency(dependency: xml.etree.ElementTree.Element) -> list[str]:
    """Parse <all>, <any_of>, and <component_dependency> manifest stanzas.

    Schema:
        <all>
          <component_dependency value="component"/>
          <component_dependency value="component"/>
          <any_of>
            <component_dependency value="component"/>
            <component_dependency value="component"/>
          </any_of>
        </all>

    Args:
        dependency: XML Element of dependency.

    Returns:
        list of component id dependencies.
    """
    if dependency.tag == 'component_dependency':
        return [dependency.attrib['value']]
    if dependency.tag == 'all':
        dependencies = []
        for subdependency in dependency:
            dependencies.extend(_parse_dependency(subdependency))
        return dependencies
    if dependency.tag == 'any_of':
        # Explicitly ignore.
        return []

    # Unknown dependency tag type.
    return []


def check_dependencies(
    root: xml.etree.ElementTree.Element,
    component_id: str,
    include: list[str],
    exclude: list[str] | None = None,
    device_core: str | None = None,
) -> bool:
    """Check the list of optional dependencies for a component.

    Verifies that the optional dependencies for a component are satisfied by
    components listed in `include` or `exclude`.

    Args:
        root: root of element tree.
        component_id: id of component to check.
        include: list of component ids included in the project.
        exclude: list of component ids explicitly excluded from the project.
        device_core: name of core to filter sources for.

    Returns:
        True if dependencies are satisfied, False if not.
    """
    xpath = f'./components/component[@id="{component_id}"]/dependencies/*'
    for dependency in root.findall(xpath):
        if not _check_dependency(
            dependency, include, exclude=exclude, device_core=device_core
        ):
            return False
    return True


def _check_dependency(
    dependency: xml.etree.ElementTree.Element,
    include: list[str],
    exclude: list[str] | None = None,
    device_core: str | None = None,
) -> bool:
    """Check a dependency for a component.

    Verifies that the given {dependency} is satisfied by components listed in
    `include` or `exclude`.

    Args:
        dependency: XML Element of dependency.
        include: list of component ids included in the project.
        exclude: list of component ids explicitly excluded from the project.
        device_core: name of core to filter sources for.

    Returns:
        True if dependencies are satisfied, False if not.
    """
    if dependency.tag == 'component_dependency':
        component_id = dependency.attrib['value']
        return component_id in include or (
            exclude is not None and component_id in exclude
        )
    if dependency.tag == 'all':
        for subdependency in dependency:
            if not _check_dependency(
                subdependency, include, exclude=exclude, device_core=device_core
            ):
                return False
        return True
    if dependency.tag == 'any_of':
        for subdependency in dependency:
            if _check_dependency(
                subdependency, include, exclude=exclude, device_core=device_core
            ):
                return True

        tree = xml.etree.ElementTree.tostring(dependency).decode('utf-8')
        print(f'Unsatisfied dependency from: {tree}', file=sys.stderr)
        return False

    # Unknown dependency tag type.
    return True


def create_project(
    root: xml.etree.ElementTree.Element,
    include: list[str],
    exclude: list[str] | None = None,
    device_core: str | None = None,
) -> tuple[
    list[str],
    list[str],
    list[pathlib.Path],
    list[pathlib.Path],
    list[pathlib.Path],
    list[pathlib.Path],
]:
    """Create a project from a list of specified components.

    Args:
        root: root of element tree.
        include: list of component ids included in the project.
        exclude: list of component ids excluded from the project.
        device_core: name of core to filter sources for.

    Returns:
        (component_ids, defines, include_paths, headers, sources, libs) for the
        project.
    """
    # Build the project list from the list of included components by expanding
    # dependencies.
    project_list = []
    pending_list = include
    while len(pending_list) > 0:
        component_id = pending_list.pop(0)
        if component_id in project_list:
            continue
        if exclude is not None and component_id in exclude:
            continue

        project_list.append(component_id)
        pending_list.extend(parse_dependencies(root, component_id))

    return (
        project_list,
        sum(
            (
                parse_defines(root, component_id, device_core=device_core)
                for component_id in project_list
            ),
            [],
        ),
        sum(
            (
                parse_include_paths(root, component_id, device_core=device_core)
                for component_id in project_list
            ),
            [],
        ),
        sum(
            (
                parse_headers(root, component_id, device_core=device_core)
                for component_id in project_list
            ),
            [],
        ),
        sum(
            (
                parse_sources(root, component_id, device_core=device_core)
                for component_id in project_list
            ),
            [],
        ),
        sum(
            (
                parse_libs(root, component_id, device_core=device_core)
                for component_id in project_list
            ),
            [],
        ),
    )


class Project:
    """Self-contained MCUXpresso project.

    Properties:
        component_ids: list of component ids compromising the project.
        defines: list of compiler definitions to build the project.
        include_dirs: list of include directory paths needed for the project.
        headers: list of header paths exported by the project.
        sources: list of source file paths built as part of the project.
        libs: list of libraries linked to the project.
        dependencies_satisfied: True if the project dependencies are satisfied.
    """

    @classmethod
    def from_file(
        cls,
        manifest_path: pathlib.Path,
        include: list[str] | None = None,
        exclude: list[str] | None = None,
        device_core: str | None = None,
    ):
        """Create a self-contained project with the specified components.

        Args:
            manifest_path: path to SDK manifest XML.
            include: list of component ids included in the project.
            exclude: list of component ids excluded from the project.
            device_core: name of core to filter sources for.
        """
        tree = xml.etree.ElementTree.parse(manifest_path)
        root = tree.getroot()
        return cls(
            root, include=include, exclude=exclude, device_core=device_core
        )

    def __init__(
        self,
        manifest: xml.etree.ElementTree.Element,
        include: list[str] | None = None,
        exclude: list[str] | None = None,
        device_core: str | None = None,
    ):
        """Create a self-contained project with the specified components.

        Args:
            manifest: parsed manifest XML.
            include: list of component ids included in the project.
            exclude: list of component ids excluded from the project.
            device_core: name of core to filter sources for.
        """
        assert (
            include is not None
        ), "Project must include at least one component."

        (
            self.component_ids,
            self.defines,
            self.include_dirs,
            self.headers,
            self.sources,
            self.libs,
        ) = create_project(
            manifest, include, exclude=exclude, device_core=device_core
        )

        for component_id in self.component_ids:
            if not check_dependencies(
                manifest,
                component_id,
                self.component_ids,
                exclude=exclude,
                device_core=device_core,
            ):
                self.dependencies_satisfied = False
                return

        self.dependencies_satisfied = True
