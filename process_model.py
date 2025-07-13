import os
import shutil
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
    with open(output_file, "wb") as file:
        file.write(rendered_content.encode('utf-8'))

    print(f"File '{output_file}' has been created with the rendered content.")


def process_properties(uml_element, id_to_name_map=None):
    """
    Process all properties of an element.

    This will remove any with an "}" in the name which catches the xml:id and xml:type.
    """
    properties = []
    property = {}

    for prop_name, prop_value in uml_element.attrib.items():

        if '}' not in prop_name:

            if prop_name not in ['sType', 'nType', 'documentation']:
                # Resolve type to an actual data type name.
                if prop_name == 'type':
                    if id_to_name_map:
                        prop_value = id_to_name_map.get(prop_value, None)

                property = {
                    'name': prop_name,
                    'value': prop_value
                }

                properties.append(property)
    return properties


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
            print ("{:44} {:20} {}".format(id, type, name))
            name_map[id] = name

    pprint(name_map)

    return name_map


def generate_enumeration_docs_new(model_file, prefix, output_path):
    """
    Generate enumeration documentation. One page per enumeration.
    """
    tree = ET.parse(model_file)
    root = tree.getroot()

    ns = { 'xmi': 'http://schema.omg.org/spec/XMI/2.1', 'uml': 'http://schema.omg.org/spec/UML/2.0' }

    # Find all Enumerations
    for packaged_element in root.findall('.//packagedElement[@xmi:type="uml:Enumeration"]', ns):

        data = {}

        enum_id = get_namespaced_attribute(packaged_element, "xmi:id", ns)
        xmi_type = get_namespaced_attribute(packaged_element, "xmi:type", ns)
        enum_name = packaged_element.get('name')

        ###############################################################################
        ##  Find the element.                                                        ##
        ###############################################################################

        element = root.find(f'.//element[@xmi:idref="{enum_id}"]', ns)
        properties = element.find('properties')

        enum_desc = properties.get('documentation')

        ###############################################################################
        ##  Add the main details of the enumeration.                                 ##
        ###############################################################################

        data['details'] = {
             'id': enum_id,
             'name': enum_name,
             'type': xmi_type,
             'model_prefix': prefix,
             'description': enum_desc
        }

        ###############################################################################
        ##  Add the properties of the enumeration.                                   ##
        ###############################################################################

        data['properties'] = process_properties(properties)

        # data['properties'] = process_properties(packaged_element)

        ###############################################################################
        ##  Loop through the ownedLiterals.                                          ##
        ###############################################################################

        data['literals'] = []
        literal = {}

        for owned_literal in packaged_element.findall('./ownedLiteral', ns):

            lit_id = get_namespaced_attribute(owned_literal, 'xmi:id', ns)
            lit_name = owned_literal.get('name')
            lit_type = owned_literal.get('type')

            ###########################################################################
            ##  Get the literal attributes.                                          ##
            ###########################################################################

            lit_data = generate_literal_page(lit_id,
                                             root,
                                             ns,
                                             prefix,
                                             os.path.join(output_path, enum_name))

            ###########################################################################
            ##  End of get the literal attributes.                                   ##
            ###########################################################################

            ###########################################################################
            ##  Add the literal attributes to the enumeration page.                  ##
            ###########################################################################

            #lit_visibility = owned_literal.get('visibility')
            #lit_description = owned_literal.get('description')

            literal = {
                'visibility': return_property(lit_data['properties'], 'scope'),
                'name': lit_name,
                'description': lit_data['details']['description']
            }

            data['literals'].append(literal)


        # pprint(data)

        output_file = os.path.join(output_path, enum_name + ".md")
        render_template("enumeration.md.j2", data, output_file)


def generate_literal_page(lit_id, root, ns, prefix, output_path):
    """
    Generate literal documentaiton. One page per literal.

    This only get the literal attributes currently. No page is generated.
    """

    owned_literal = root.find(f'.//ownedLiteral[@xmi:id="{lit_id}"]', ns)
    literal = root.find(f'.//attribute[@xmi:idref="{lit_id}"]', ns)
    documentation = literal.find('documentation')
    properties = literal.find('properties')
    bounds = literal.find('bounds')

    lit_data = {}

    lit_name = literal.get('name')
    xmi_type = get_namespaced_attribute(owned_literal, "xmi:type", ns)
    lit_desc = documentation.get('value')

    lit_data['details'] = {
        'id': lit_id,
        'name': lit_name,
        'model_prefix': prefix,
        'type': xmi_type,
        'description': lit_desc
    }

    lit_data['properties'] = process_properties(properties)

    lit_data['properties'].append({ 'name': 'bounds', 'value': bounds.get('lower') + ".." + bounds.get('upper') })
    lit_data['properties'].append({ 'name': 'idref', 'value': lit_id })
    lit_data['properties'].append({ 'name': 'scope', 'value': literal.get('scope') })

    return lit_data


def generate_attribute_page(attr_id, root, ns, prefix, output_path):
    """
    Generate attribute documentation. One page per attribute.
    """

    print(">>>>>", attr_id)

    owned_attribute = root.find(f'.//ownedAttribute[@xmi:id="{attr_id}"]', ns)
    attribute = root.find(f'.//attribute[@xmi:idref="{attr_id}"]', ns)
    documentation = attribute.find('documentation')
    properties = attribute.find('properties')
    bounds = attribute.find('bounds')

    attr_data = {}

    attr_name = attribute.get('name')
    xmi_type = get_namespaced_attribute(owned_attribute, "xmi:type", ns)
    attr_desc = documentation.get('value')

    # attr_desc = root.find(f'.//attribute[@xmi:idref="{attr_id}"]/documentation', ns).attrib.get('value')

    attr_data['details'] = {
        'id': attr_id,
        'name': attr_name,
        'model_prefix': prefix,
        'type': xmi_type,
        'description': attr_desc
    }

    attr_data['properties'] = process_properties(properties)

    attr_data['properties'].append({ 'name': 'bounds', 'value': bounds.get('lower') + ".." + bounds.get('upper') })
    attr_data['properties'].append({ 'name': 'idref', 'value': attr_id })
    attr_data['properties'].append({ 'name': 'scope', 'value': attribute.get('scope') })

    pprint(attr_data)
    os.makedirs(output_path, exist_ok=True)
    output_file = os.path.join(output_path, attr_name + ".md")
    render_template("attribute.md.j2", attr_data, output_file)

    print("*****")

    attr = root.find(f'.//attribute[@xmi:idref="{attr_id}"]', ns)

    # for element in attr:
    #     print(element)
    #     for at in element.attrib.items():
    #         print(at)

    print("*****")

    return attr_data


def return_property(properties, property_name):
    """
    Helper function to return a property value from our constructed page data.
    """

    value = None

    for prop in properties:
        if prop.get("name") == property_name:
            value = prop.get("value")
            break

    return value

def generate_class_docs(model_file, prefix, output_path):
    """
    Generate class documentation. One page per class.
    """
    tree = ET.parse(model_file)
    root = tree.getroot()

    ns = { 'xmi': 'http://schema.omg.org/spec/XMI/2.1', 'uml': 'http://schema.omg.org/spec/UML/2.0' }

    id_to_name_map = generate_id_to_name_map(root, ns)

    # Find all Classes
    for packaged_element in root.findall('.//packagedElement[@xmi:type="uml:Class"]', ns):

        data = {}

        class_id = get_namespaced_attribute(packaged_element, "xmi:id", ns)
        xmi_type = get_namespaced_attribute(packaged_element, "xmi:type", ns)
        class_name = packaged_element.get('name')

        ###############################################################################
        ##  Find the element and extract properties.                                 ##
        ###############################################################################

        element = root.find(f'.//element[@xmi:idref="{class_id}"]', ns)
        properties = element.find('properties')
        links = element.find('links')

        class_desc = properties.get('documentation')

        print(">> Processing class: ", class_name)

        ###############################################################################
        ##  Add main details of the class.                                           ##
        ###############################################################################

        data['details'] = {
            'id': class_id,
            'name': class_name,
            'type': xmi_type,
            'model_prefix': prefix,
            'description': class_desc
        }

        ###############################################################################
        ##  Add the class properties.                                                ##
        ###############################################################################

        # data['properties'] = process_properties(packaged_element)

        data['properties'] = process_properties(properties)

        ###############################################################################
        ##  Add the class operations.                                                ##
        ###############################################################################

        data['operations'] = []

        for op in packaged_element.findall('./ownedOperation', ns):
            data['operations'].append({'name': op.get('name')})

        ###############################################################################
        ##  Add the class relationships.                                             ##
        ###############################################################################

        print(links)

        if links is not None:
            data['relationships'] = []

            for association in links.findall('./Association', ns):
                relationship = {
                    'start': id_to_name_map.get(association.get('start')),
                    'end': id_to_name_map.get(association.get('end'))
                }
                data['relationships'].append(relationship)

        pprint(data)

        ###############################################################################
        ##  Loop through the ownedAttributes.                                        ##
        ###############################################################################

        data['attributes'] = []
        attribute = {}

        for owned_attibute in packaged_element.findall('./ownedAttribute', ns):

            print("ownedAttribute Name: ", owned_attibute.get('name'))

            # Sparx Enterprise Architect puts associations as ownedAttribute of type uml:Property as well
            if not owned_attibute.get('association'):

                attr_id = get_namespaced_attribute(owned_attibute, 'xmi:id', ns)
                attr_name = owned_attibute.get('name')

                #######################################################################
                ##  Generate of the attribute page.                                  ##
                #######################################################################

                attr_data = generate_attribute_page(attr_id,
                                                    root,
                                                    ns,
                                                    prefix,
                                                    os.path.join(output_path, class_name))

                #######################################################################
                ##  End of attribute page generation.                                ##
                #######################################################################

                #######################################################################
                ##  Add attributes for class page.                                   ##
                #######################################################################

                attribute = {
                    'visibility': return_property(attr_data['properties'], 'scope'),
                    'name': attr_name,
                    'type': return_property(attr_data['properties'], 'type'),
                    'description': attr_data['details']['description'],
                }

                data['attributes'].append(attribute)

        ###############################################################################
        ##  Back to handling the Class.                                              ##
        ###############################################################################

        os.makedirs(os.path.join(output_path, class_name), exist_ok=True)
        output_file = os.path.join(output_path, class_name, "index.md")
        render_template("class.md.j2", data, output_file)


def generate_datatype_docs(model_file, prefix, output_path):
    """
    Generate data type documentation. One page per data type.
    """
    print("Processing DataTypes")

    tree = ET.parse(model_file)
    root = tree.getroot()

    ns = { 'xmi': 'http://schema.omg.org/spec/XMI/2.1', 'uml': 'http://schema.omg.org/spec/UML/2.0' }

    id_to_name_map = generate_id_to_name_map(root, ns)

    os.makedirs(os.path.join(output_path, "classes"), exist_ok=True)

    # Find all DataTypes
    for packaged_element in root.findall('.//packagedElement[@xmi:type="uml:DataType"]', ns):

        data = {}

        datatype_id = get_namespaced_attribute(packaged_element, "xmi:id", ns)
        xmi_type = get_namespaced_attribute(packaged_element, "xmi:type", ns)
        datatype_name = packaged_element.get('name')

        ###############################################################################
        ##  Find the element and extract properties.                                 ##
        ###############################################################################

        element = root.find(f'.//element[@xmi:idref="{datatype_id}"]', ns)
        properties = element.find('properties')
        links = element.find('links')

        datatype_desc = properties.get('documentation')

        ###############################################################################
        ##  Add the main details of the datatype.                                    ##
        ###############################################################################

        data['details'] = {
            'id': datatype_id,
            'name': datatype_name,
            'model_prefix': prefix,
            'type': xmi_type,
            'description': datatype_desc
        }

        ###############################################################################
        ##  Add the properties of the datatype.                                      ##
        ###############################################################################

        # data['properties'] = process_properties(packaged_element)

        data['properties'] = process_properties(properties)

        ###############################################################################
        ##  Add the generalized elements of the datatype.                            ##
        ###############################################################################

        data['generalized_elements'] = []

        for gen in packaged_element.findall('./generalization', ns):
            data['generalized_elements'].append(id_to_name_map.get(gen.get('general'), None))

        ###############################################################################
        ##  Add the specialized elements of the datatype.                            ##
        ###############################################################################

        # TODO: complete this

        ###############################################################################
        ##  Add the datatype relationships.                                          ##
        ###############################################################################

        print(links)

        if links is not None:
            data['relationships'] = []

            for generalization in links.findall('./Generalization', ns):
                relationship = {
                    'start': id_to_name_map.get(generalization.get('start')),
                    'end': id_to_name_map.get(generalization.get('end'))
                }
                data['relationships'].append(relationship)

        pprint(data)

        output_file = os.path.join(output_path, datatype_name + ".md")
        render_template("datatype.md.j2", data, output_file)

    # Find all PrimitiveType elements
    for packaged_element in root.findall('.//packagedElement[@xmi:type="uml:PrimitiveType"]', ns):

        data = {}

        datatype_id = get_namespaced_attribute(packaged_element, "xmi:id", ns)
        xmi_type = get_namespaced_attribute(packaged_element, "xmi:type", ns)
        datatype_name = packaged_element.get('name')

        data['details'] = {
            'id': datatype_id,
            'name': datatype_name,
            'type': xmi_type,
            'model_prefix': prefix,
            'description': None
        }

        ###############################################################################
        ##  Add the generalization elements of the datatype.                         ##
        ###############################################################################

        data['generalized_elements'] = []

        for generalization in packaged_element.findall('./generalization', ns):
            data['generalized_elements'].append(get_namespaced_attribute(generalization, "xmi:id", ns))

        ###############################################################################
        ##  Add the properties elements of the datatype.                             ##
        ###############################################################################

        data['properties'] = process_properties(packaged_element)

        data['properties'].append({ 'name': datatype_id })

        pprint(data)

        output_file = os.path.join(output_path, datatype_name + ".md")
        render_template("datatype.md.j2", data, output_file)


def generate_diagram_pages(model_file, prefix, output_path):
    """
    Generate diagram pages.
    """

    tree = ET.parse(model_file)
    root = tree.getroot()

    ns = { 'xmi': 'http://schema.omg.org/spec/XMI/2.1', 'uml': 'http://schema.omg.org/spec/UML/2.0' }

    id_to_name_map = generate_id_to_name_map(root, ns)

    os.makedirs(os.path.join(output_path, "images"), exist_ok=True)

    # Find all DataTypes
    for diagram in root.findall('.//diagram', ns):
        id = get_namespaced_attribute(diagram, 'xmi:id', ns)
        properties = diagram.find('properties')

        name = properties.get('name')

        data = {
            'id': id,
            'name': name,
            'model_prefix': prefix
        }

        shutil.copy(os.path.join("model", "Images", id + ".png"), os.path.join(output_path, "images"))

        output_file = os.path.join(output_path, name.lower() + "_diagram.md")
        render_template("diagram.md.j2", data, output_file)


def generate_package_page(package, model_file, prefix, output_path):
    """
    Generate package pages.
    """

    tree = ET.parse(model_file)
    root = tree.getroot()

    ns = { 'xmi': 'http://schema.omg.org/spec/XMI/2.1', 'uml': 'http://schema.omg.org/spec/UML/2.0' }

    id_to_name_map = generate_id_to_name_map(root, ns)

    os.makedirs(os.path.join(output_path, package.lower()), exist_ok=True)

    print("Finding", package)

    str = f'.//packagedElement[@xmi:type="uml:Package"][name="{package}"]'

    print(str)

    # Find all Enumerations
    # for packaged_element in root.findall(f'.//packagedElement[@xmi:type="uml:Package"][name="{package}"]', ns):
    for packaged_element in root.findall('.//packagedElement[@xmi:type="uml:Package"]', ns):

        data = {}

        package_id = get_namespaced_attribute(packaged_element, 'xmi:id', ns)
        xmi_type = get_namespaced_attribute(packaged_element, "xmi:type", ns)
        package_name = packaged_element.get('name')

        print("Found package", package_name)

        if package_name == package:

            ###############################################################################
            ##  Find the element and extract properties.                                 ##
            ###############################################################################

            element = root.find(f'.//element[@xmi:idref="{package_id}"]', ns)
            properties = element.find('properties')

            # package_desc = properties.get('documentation')

            ###############################################################################
            ##  Add the main details of the package.                                     ##
            ###############################################################################

            name = properties.get('name')

            data['details'] = {
                'id': package_id,
                'name': package_name,
                'model_prefix': prefix,
                'type': xmi_type,
                'description': None
            }

            ###############################################################################
            ##  Add the properties of the datatype.                                      ##
            ###############################################################################

            # data['properties'] = process_properties(packaged_element)

            # data['properties'] = process_properties(properties)

            data['properties'] = [
                { "name": "name", "value": package_name },
                { "name": 'stereotype', "value": None },
                { "name": 'visibility', "value": properties.get('scope') },
                { "name": 'importedElements', "value": "" },
            ]

            ###############################################################################
            ##  Add all the owned elements of the package.                               ##
            ###############################################################################

            data['owned_elements'] = []

            for owned in packaged_element.findall('./packagedElement', ns):
                if get_namespaced_attribute(owned, 'xmi:type', ns) != 'uml:Association':
                    data['owned_elements'].append({
                        'name': owned.get('name', None),
                        'type': get_namespaced_attribute(owned, 'xmi:type', ns)
                    })
                    #data['owned_elements'].append(id_to_name_map.get(owned.get('name'), None))

            pprint(data)

            output_file = os.path.join(output_path, package_name.lower(), "index.md")
            render_template("package.md.j2", data, output_file)


def main():
#   model_file = "TransportSafetyModel.xmi"
    model_file = os.path.join("model", "model_uml2.2_xmi_2.1_EA.xmi")
    output_dir = "output"
    prefix = "TSM"

    #generate_enumeration_docs_new(model_file, prefix, os.path.join(output_dir, "enumerations"))
    #generate_class_docs(model_file, prefix, os.path.join(output_dir, "classes"))
    #generate_datatype_docs(model_file, prefix, os.path.join(output_dir, "datatypes"))
    #generate_diagram_pages(model_file, prefix, output_dir)
    generate_package_page("Enumerations", model_file, prefix, output_dir)
    generate_package_page("DataTypes", model_file, prefix, output_dir)
    generate_package_page("Classes", model_file, prefix, output_dir)

if __name__ == "__main__":
    main()