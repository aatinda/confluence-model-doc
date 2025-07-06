import os
import xml.etree.ElementTree as ET

from jinja2 import Template, FileSystemLoader, Environment
from pprint import pprint

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
    with open(output_file, "w") as file:
        file.write(rendered_content)

    print(f"File '{output_file}' has been created with the rendered content.")


def process_properties(uml_element, datatype_map=None):
    """
    Process all properties of an element.

    This will remove any with an "}" in the name which catches the xml:id and xml:type.
    """
    properties = []
    property = {}

    for prop_name, prop_value in uml_element.attrib.items():

        if '}' not in prop_name:

            # Resolve type to an actual data type name.
            if prop_name == 'type':
                prop_value = datatype_map.get(prop_value, None)

            property = {
                'name': prop_name,
                'value': prop_value
            }

            properties.append(property)
    return properties


def generate_datatype_map(root, ns):
    """
    Return a dictionary mapping data type ID to name.
    """
    # Find all DataTypes elements
    datatype_map = {}

    for uml_datatype in root.findall('.//packagedElement[@xmi:type="uml:DataType"]', ns):
        #for attr_name, attr_value in uml_datatype.attrib.items():
        #    print(f"Attribute Name: {attr_name}, Attribute Value: {attr_value}")
        datatype_id = get_namespaced_attribute(uml_datatype, "xmi:id", ns)
        datatype_name = uml_datatype.get('name')
        datatype_map[datatype_id] = datatype_name
        # print("{} - {}".format(datatype_id, datatype_name))

    # Find all Enumerations
    for uml_enum in root.findall('.//packagedElement[@xmi:type="uml:Enumeration"]', ns):
        #for attr_name, attr_value in uml_datatype.attrib.items():
        #    print(f"Attribute Name: {attr_name}, Attribute Value: {attr_value}")
        enum_id = get_namespaced_attribute(uml_enum, "xmi:id", ns)
        enum_name = uml_enum.get('name')
        datatype_map[enum_id] = enum_name

    pprint(datatype_map)

    return datatype_map


def generate_enumeration_docs_new(model_file, output_path):
    """
    Generate enumeration documentation. One page per enumeration.
    """
    tree = ET.parse(model_file)
    root = tree.getroot()

    ns = { 'xmi': 'http://schema.omg.org/spec/XMI/2.1', 'uml': 'http://schema.omg.org/spec/UML/2.0' }

    # Find all Enumerations
    for uml_enum in root.findall('.//packagedElement[@xmi:type="uml:Enumeration"]', ns):

        data = {}

        enum_id = get_namespaced_attribute(uml_enum, "xmi:id", ns)
        enum_name = uml_enum.get('name')

        data['details'] = {
            'name': enum_name,
            'description': None
        }

        # Literals

        data['literals'] = []
        literal = {}

        for literal in uml_enum.findall('./ownedLiteral', ns):

            lit_name = literal.get('name')
            lit_visibility = literal.get('visibility')
            lit_description = literal.get('description')

            literal = {
                'name': lit_name,
                'visibility': lit_visibility,
                'description': lit_description
            }

            data['literals'].append(literal)

        # Properties

        data['properties'] = process_properties(uml_enum)

        pprint(data)

        output_file = os.path.join(output_path, enum_name + ".md")
        render_template("enumeration.md.j2", data, output_file)


def generate_class_docs(model_file, output_path):
    """
    Generate class documentation. One page per class.
    """
    tree = ET.parse(model_file)
    root = tree.getroot()

    ns = { 'xmi': 'http://schema.omg.org/spec/XMI/2.1', 'uml': 'http://schema.omg.org/spec/UML/2.0' }

    datatype_map = generate_datatype_map(root, ns)

    # Find all UML Class elements
    for uml_class in root.findall('.//packagedElement[@xmi:type="uml:Class"]', ns):

        data = {}

        class_name = uml_class.get('name')

        data['details'] = {
            'name': class_name,
            'description': None
        }

        # Attributes
        data['attributes'] = []
        attribute = {}

        for attr in uml_class.findall('./ownedAttribute', ns):

            ###############################################################
            # Generate the attribute page.

            attr_data = {}

            attr_data['details'] = {
                'name': attr.get('name'),
                'description': None
            }

            attr_data['properties'] = process_properties(attr, datatype_map)

            os.makedirs(os.path.join(output_path, class_name), exist_ok=True)
            output_file = os.path.join(output_path, class_name, attr.get('name') + ".md")
            render_template("attribute.md.j2", attr_data, output_file)

            #
            ###############################################################

            attr_name = attr.get('name')
            attr_type = datatype_map.get(attr.get('type'), None)
            attr_visibility = attr.get('visibility')
            attr_description = attr.get('description')

            attribute = {
                'visibility': attr_visibility,
                'name': attr_name,
                'type': attr_type,
                'description': attr_description
            }

            data['attributes'].append(attribute)

        # Properties
        data['properties'] = process_properties(uml_class)

        # Operations
        data['operations'] = []

        for op in uml_class.findall('./ownedOperation', ns):
            data['operations'].append({'name': op.get('name')})

        pprint(data)

        os.makedirs(os.path.join(output_path, class_name), exist_ok=True)
        output_file = os.path.join(output_path, class_name, "index.md")
        render_template("class.md.j2", data, output_file)



def generate_datatype_docs(model_file, output_path):
    """
    Generate data type documentation. One page per data type.
    """
    tree = ET.parse(model_file)
    root = tree.getroot()

    ns = { 'xmi': 'http://schema.omg.org/spec/XMI/2.1', 'uml': 'http://schema.omg.org/spec/UML/2.0' }

    datatype_map = generate_datatype_map(root, ns)

    # Find all UML DataType elements
    for uml_datatype in root.findall('.//packagedElement[@xmi:type="uml:DataType"]', ns):

        data = {}

        datatype_name = uml_datatype.get('name')

        data['details'] = {
            'name': datatype_name,
            'description': None
        }

        # Generalized Elements

        data['generalized_elements'] = []

        for gen in uml_datatype.findall('./generalization', ns):

            data['generalized_elements'].append(datatype_map.get(gen.get('general'), None))

        # Specialized Elements
        # TODO: complete this

        # Properties

        data['properties'] = process_properties(uml_datatype)

        pprint(data)

        output_file = os.path.join(output_path, datatype_name + ".md")
        render_template("datatype.md.j2", data, output_file)


def main():
    model_file = "TransportSafetyModel.xmi"
    output_dir = "output"

    generate_enumeration_docs_new(model_file, os.path.join(output_dir, "enumerations"))
    generate_class_docs(model_file, os.path.join(output_dir, "classes"))
    generate_datatype_docs(model_file, os.path.join(output_dir, "datatypes"))


if __name__ == "__main__":
    main()