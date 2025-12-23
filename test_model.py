import os
import shutil
# import xml.etree.ElementTree as ET

from lxml import etree as ET

from jinja2 import Template, FileSystemLoader, Environment
from pprint import pprint


OUTPUT_DIR = "output"
PREFIX = "TSM"
NS = { 'xmi': 'http://schema.omg.org/spec/XMI/2.1', 'uml': 'http://schema.omg.org/spec/UML/2.1' }


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

def generate_enumeration_page(root, packaged_element, parent_package, parent_map: dict):

    """
    Generate enumeration documentation. One page per enumeration.
    """

    data = {}

    enum_id = get_namespaced_attribute(packaged_element, "xmi:id", NS)
    xmi_type = get_namespaced_attribute(packaged_element, "xmi:type", NS)
    enum_name = packaged_element.get('name')

    print(enum_id)
    print(xmi_type)
    print(enum_name)

    ###############################################################################
    ##  Find the element.                                                        ##
    ###############################################################################

    element = root.find(f'.//element[@xmi:idref="{enum_id}"]', NS)
    properties = element.find('properties')

    # enum_desc = properties.get('documentation')
    enum_desc = element.find('./tags/tag[@name="definition"]').get('value')

    ###############################################################################
    ##  Add the main details of the enumeration.                                 ##
    ###############################################################################

    data['details'] = {
            'id': enum_id,
            'name': enum_name,
            'type': xmi_type,
            'model_prefix': PREFIX,
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

    for owned_literal in packaged_element.findall('./ownedLiteral', NS):

        lit_id = get_namespaced_attribute(owned_literal, 'xmi:id', NS)
        lit_name = owned_literal.get('name')
        lit_type = owned_literal.get('type')

        ###########################################################################
        ##  Get the literal attributes.                                          ##
        ###########################################################################

        lit_data = get_literal_data(lit_id, root)

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

    output_path = os.path.join(*get_path_to_root(parent_package, parent_map))
    output_file = os.path.join(output_path, enum_name + ".md")

    print(output_file)
    print(output_path)
    print(enum_name)
    render_template("enumeration.md.j2", data, output_file)


def get_literal_data(lit_id, root):
    """
    Generate literal documentaiton. One page per literal.

    This only gets the literal attributes currently. No page is generated.
    """

    owned_literal = root.find(f'.//ownedLiteral[@xmi:id="{lit_id}"]', NS)
    literal = root.find(f'.//attribute[@xmi:idref="{lit_id}"]', NS)
    documentation = literal.find('documentation')
    properties = literal.find('properties')
    bounds = literal.find('bounds')

    lit_data = {}

    lit_name = literal.get('name')
    xmi_type = get_namespaced_attribute(owned_literal, "xmi:type", NS)
    # lit_desc = documentation.get('value')
    lit_desc = literal.find('./tags/tag[@name="definition"]').get('value')

    lit_data['details'] = {
        'id': lit_id,
        'name': lit_name,
        'model_prefix': PREFIX,
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

def generate_class_page(root, packaged_element, parent_package, parent_map: dict):
    """
    Generate class documentation. One page per class.
    """

    id_to_name_map = generate_id_to_name_map(root, NS)

    data = {}

    class_id = get_namespaced_attribute(packaged_element, "xmi:id", NS)
    xmi_type = get_namespaced_attribute(packaged_element, "xmi:type", NS)
    class_name = packaged_element.get('name')

    ###############################################################################
    ##  Find the element and extract properties.                                 ##
    ###############################################################################

    element = root.find(f'.//element[@xmi:idref="{class_id}"]', NS)
    properties = element.find('properties')
    links = element.find('links')

    # class_desc = properties.get('documentation')
    class_desc = element.find('./tags/tag[@name="definition"]').get('value')

    print(">> Processing class: ", class_name)

    ###############################################################################
    ##  Add main details of the class.                                           ##
    ###############################################################################

    data['details'] = {
        'id': class_id,
        'name': class_name,
        'type': xmi_type,
        'model_prefix': PREFIX,
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

    for op in packaged_element.findall('./ownedOperation', NS):
        data['operations'].append({'name': op.get('name')})

    ###############################################################################
    ##  Add the class relationships.                                             ##
    ###############################################################################

    print(links)

    if links is not None:
        data['relationships'] = []

        for association in links.findall('./Association', NS):
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

    for owned_attibute in packaged_element.findall('./ownedAttribute', NS):

        print("ownedAttribute Name: ", owned_attibute.get('name'))

        # Sparx Enterprise Architect puts associations as ownedAttribute of type uml:Property as well
        if not owned_attibute.get('association'):

            attr_id = get_namespaced_attribute(owned_attibute, 'xmi:id', NS)
            attr_name = owned_attibute.get('name')

            #######################################################################
            ##  Generate of the attribute page.                                  ##
            #######################################################################

            output_path = os.path.join(*get_path_to_root(parent_package, parent_map))

            attr_data = generate_attribute_page(attr_id,
                                                root,
                                                NS,
                                                PREFIX,
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

    output_path = os.path.join(*get_path_to_root(parent_package, parent_map))
    os.makedirs(os.path.join(output_path, class_name), exist_ok=True)
    output_file = os.path.join(output_path, class_name, "index.md")
    render_template("class.md.j2", data, output_file)


def generate_datatype_pages(model_file, prefix, output_path):
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


def generate_package_page(root, packaged_element, parent_map: dict):
    """
    Generate package pages.

    Accepts the packagedElement of xmi:type uml:package.
    """

    data = {}

    package_id = get_namespaced_attribute(packaged_element, 'xmi:id', NS)
    xmi_type = get_namespaced_attribute(packaged_element, "xmi:type", NS)
    package_name = packaged_element.get('name')

    print("Generating package page for {}".format(package_name))

    # if parent_element is not None:
    #     parent_name = parent_element.get('name')
    #     output_path = os.path.join(OUTPUT_DIR, parent_name, package_name)
    # else:
    #     output_path = os.path.join(OUTPUT_DIR, package_name)

    output_path = os.path.join(*get_path_to_root(package_name, parent_map))

    os.makedirs(output_path, exist_ok=True)

    ###############################################################################
    ##  Find the element and extract properties.                                 ##
    ###############################################################################

    element = root.find(f'.//element[@xmi:idref="{package_id}"]', NS)
    properties = element.find('properties')

    package_desc = element.find('./tags/tag[@name="definition"]').get('value')
    # package_desc = properties.get('documentation')

    ###############################################################################
    ##  Add the main details of the package.                                     ##
    ###############################################################################

    name = properties.get('name')

    data['details'] = {
        'id': package_id,
        'name': package_name,
        'model_prefix': PREFIX,
        'type': xmi_type,
        'description': package_desc,
    }

    ###############################################################################
    ##  Add the properties of the datatype.                                      ##
    ###############################################################################

    # data['properties'] = process_properties(packaged_element)

    # data['properties'] = process_properties(properties)

    data['properties'] = [
        { "name": "name", "value": package_name },
        { "name": 'stereotype', "value": properties.get('stereotype') },
        { "name": 'visibility', "value": properties.get('scope') },
        { "name": 'importedElements', "value": "" },
    ]

    ###############################################################################
    ##  Add all the owned elements of the package.                               ##
    ###############################################################################

    data['owned_elements'] = []

    for owned in packaged_element.findall('./packagedElement', NS):
        if get_namespaced_attribute(owned, 'xmi:type', NS) not in ['uml:Association',
                                                                   'uml:Usage']:
            data['owned_elements'].append({
                'name': owned.get('name', None),
                'type': get_namespaced_attribute(owned, 'xmi:type', NS)
            })
            #data['owned_elements'].append(id_to_name_map.get(owned.get('name'), None))

    # pprint(data)

    output_file = os.path.join(output_path, "index.md")
    render_template("package.md.j2", data, output_file)


def get_path_to_root(start_node: str, parent_map: dict) -> list:
    """
    This takes a start node and a dictionary containing Child: Parent relationships and returns the 
    a list of the path to the root.
    """

    path = [start_node]
    current_node = start_node

    while current_node in parent_map:
        parent = parent_map[current_node]
        path.append(parent)
        current_node = parent
    return path[::-1]


def loop_through_packages(model_file: str):
    """
    Take a model XMI file and find the root at packagedElement of name PayloadPublication and
    then start recursing through the uml:Packages.
    """

    tree = ET.parse(model_file)
    root = tree.getroot()

    # id_to_name_map = generate_id_to_name_map(root, ns)

    # element = root.find(f'.//uml:Model/', ns)
    element = root.find(f'.//uml:Model/*/packagedElement[@name="PayloadPublication"]', NS)

    print(element)

    recurse(root, element, None, None)


def recurse(root, packaged_element, parent_element, parent_map: dict, level=0):

    indent = "  " * level

    package_id = get_namespaced_attribute(packaged_element, "xmi:id", NS)
    package_name = packaged_element.get('name')
    package_type = get_namespaced_attribute(packaged_element, "xmi:type", NS)

    if parent_element is not None:
        parent_name = parent_element.get('name')
        # parent_list = parent_list + 
        parent_map[package_name] = parent_name
    else:
        parent_name = 'root'
        parent_map = {package_name: 'root'}

    print(f"{indent}Level: {level}, ID: {package_id}, Name: {package_name}, Type: {package_type}, Parent: {parent_name}")
    print(f"{indent}Parent: {get_path_to_root(package_name, parent_map)}")

    #####################################################################################
    ##   Generate a package page.                                                      ##
    #####################################################################################

    generate_package_page(root, packaged_element, parent_map)

    #####################################################################################
    ##                                                                                 ##
    ##   Process direct child elements of a uml:Package.                               ##
    ##                                                                                 ##
    ##   This will process uml:Class and the properties (ownedAttribute) under each    ##
    ##   uml:Class directly under a class.                                             ##
    ##                                                                                 ##
    #####################################################################################

    # List all direct child elements
    print(f"{indent}Listing all child packagedElement of {package_name}")

    for child_element in packaged_element.findall("./packagedElement"):
        # Should select just uml:Class here
        element_id = get_namespaced_attribute(child_element, "xmi:id", NS)
        element_name = child_element.get('name')
        element_type = get_namespaced_attribute(child_element, "xmi:type", NS)
        print(f"{indent}>> ID: {element_id}, Name: {element_name}, Type: {element_type}")

        #################################################################################
        ##   Generate an enumeration page.                                             ##
        #################################################################################

        if element_type == "uml:Enumeration":
            generate_enumeration_page(root, child_element, package_name, parent_map)

        #################################################################################
        ##   Generate a class page.                                                    ##
        #################################################################################

        # List all properties of a class
        elif element_type == "uml:Class":

            generate_class_page(root, child_element, package_name, parent_map)

            # print(f"{indent}Listing all child ownedAttributes of class {package_name}")
            for child_attribute in child_element.findall("./ownedAttribute"):
                if not child_attribute.get('association'):
                    #print("association")
                    attr_id = get_namespaced_attribute(child_attribute, "xmi:id", NS)
                    attr_name = child_attribute.get('name')
                    attr_type = get_namespaced_attribute(child_attribute, "xmi:type", NS)
                    print(f"{indent}   ## ID: {attr_id}, Name: {attr_name}, Type: {attr_type}")
            # print(f"{indent}Listing all child ownedAttributes of class {package_name}")



    print(f"{indent}Done with child packagedElement")

    # Now find all child packages
    for child_package in packaged_element.findall('./packagedElement[@xmi:type="uml:Package"]', NS):
        recurse(root, child_package, packaged_element, parent_map, level + 1)


def main():
    """
    Main entry point.
    """
    model_file = os.path.join("model", "TransportSafetyModel_current_2025-10-16.xmi")

    loop_through_packages(model_file)


if __name__ == "__main__":
    main()