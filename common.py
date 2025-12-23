"""
Common functions used for generating Sparx Enterprise Architect model documents.
"""

import os
import shutil

from datetime import datetime
from jinja2 import FileSystemLoader, Environment
from pprint import pprint


ns = { 'xmi': 'http://schema.omg.org/spec/XMI/2.1', 'uml': 'http://schema.omg.org/spec/UML/2.1' }


def get_package_hierachy(packaged_element):

    package_hierarchy = []

    # Traverse and print the hierarchy of parents
    current_element = packaged_element
    while current_element is not None:
        xmi_type = get_namespaced_attribute(current_element, "xmi:type", ns)
        if xmi_type == 'uml:Package':
            # print("{} {}".format(current_element.tag, current_element.get('name')))
            package_hierarchy.insert(0, current_element.get('name'))
        current_element = current_element.getparent()

    print(package_hierarchy, packaged_element.get('name'))

    return package_hierarchy


def check_for_skip(package_hierarchy):
    if package_hierarchy[0:2] == ['D2Payload', 'LocationReferencing'] or \
       package_hierarchy[0:3] == ['D2Payload', 'Common', 'Classes']:
        return True
    else:
        False


def get_namespaced_attribute(element, prefix_attr_name, ns_map):
    """
    Gets a namespaced attribute from an Element, expanding the namespace automatically.
    """
    parts = prefix_attr_name.split(':', 1)
    if len(parts) == 2:
        prefix, attr_name = parts
        if prefix in ns_map:
            expanded_attr_name = f"{{{ns_map[prefix]}}}{attr_name}"
            return element.attrib.get(expanded_attr_name)
    # If no prefix, or prefix not in map, try to get as a regular attribute
    return element.attrib.get(prefix_attr_name)


def render_template(template, data, output_file):
    """
    Render the Jinja2 template and generate and output file.
    """
    env = Environment(loader=FileSystemLoader("templates"), trim_blocks=True, lstrip_blocks=True)
    template = env.get_template(template)

    # Render the template with the data
    rendered_content = template.render(data)

    # Write the rendered content to a file
    with open(output_file, "wb") as file:
        file.write(rendered_content.encode('utf-8'))

    print(f"File '{output_file}' has been created with the rendered content.")


def generate_id_to_name_map(root, ns):
    """
    Return a dictionary mapping data type ID to name.
    """
    name_map = {}

    for packaged_element in root.findall('.//packagedElement', ns):
        id = get_namespaced_attribute(packaged_element, "xmi:id", ns)
        type = get_namespaced_attribute(packaged_element, "xmi:type", ns)
        name = packaged_element.get('name')
        if type in ['uml:Enumeration', 'uml:Package', 'uml:DataType', 'uml:Class']:
            # print ("{:44} {:20} {}".format(id, type, name))
            name_map[id] = name

    # pprint(name_map)

    return name_map


def backup_and_clean_output(output_dir):
    """
    If the output directory exists then create a backup appending a date and timestamp to the end. 
    """

    if os.path.isdir(output_dir):
        now = datetime.now()
        timestamp_str = now.strftime("%Y-%m-%d_%H-%M-%S")
        backup_dir_name = output_dir + "_" + timestamp_str
        
        #os.makedirs(backup_dir_name, exist_ok=True)
        shutil.copytree(output_dir, backup_dir_name)

        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
            print(f"Folder '{output_dir}' deleted.")

        os.makedirs(output_dir)
        print(f"Folder '{output_dir}' recreated.")  