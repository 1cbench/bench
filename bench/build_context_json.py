import json
import xml.etree.ElementTree as ET
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

class C1ContextBuilder:
    """
    Converts a list of 1C identifiers into their JSON representation
    based on the config storage metadata.
    """

    def __init__(self, config_path: str = r"C:\Work\projects\sberdevices\dev\1cbench\cfg"):
        """
        Initialize the context builder with config storage path.

        Args:
            config_path: Path to the 1C configuration metadata directory
        """
        self.config_path = Path(config_path)
        self.namespace = {
            '': 'http://v8.1c.ru/8.3/MDClasses',  # Default namespace
            'v8': 'http://v8.1c.ru/8.1/data/core',
            'cfg': 'http://v8.1c.ru/8.1/data/enterprise/current-config',
            'xr': 'http://v8.1c.ru/8.3/xcf/readable',
            'xs': 'http://www.w3.org/2001/XMLSchema'
        }

    def parse_identifier(self, identifier: str) -> tuple[str, str]:
        """
        Parse a 1C identifier to extract object type and name.

        Args:
            identifier: 1C identifier like "РегистрСведений.ЦеныТоваров"

        Returns:
            Tuple of (object_type, object_name)
        """
        if '.' in identifier:
            object_type, object_name = identifier.split('.', 1)
        else:
            object_type = identifier
            object_name = ""

        return object_type, object_name

    def get_metadata_file_path(self, object_type: str, object_name: str) -> Optional[Path]:
        """
        Get the XML metadata file path for a given object.

        Args:
            object_type: Type of 1C object (e.g., "РегистрСведений")
            object_name: Name of the object (e.g., "ЦеныТоваров")

        Returns:
            Path to the XML file or None if not found
        """
        # Map 1C object types to directory names
        type_mapping = {
            'РегистрСведений': 'InformationRegisters',
            'Справочник': 'Catalogs',
            'Документ': 'Documents',
            'РегистрНакопления': 'AccumulationRegisters',
            'Константа': 'Constants',
            'Перечисление': 'Enums',
            'ПланОбмена': 'ExchangePlans',
            'Отчет': 'Reports',
            'Обработка': 'DataProcessors',
            'РегистрБухгалтерии': 'AccountingRegisters',
            'ПланСчетов': 'ChartsOfAccounts',
            'ПланВидовХарактеристик': 'ChartsOfCharacteristicTypes',
            'ПланВидовРасчета': 'ChartsOfCalculationTypes',
            'БизнесПроцесс': 'BusinessProcesses',
            'Задача': 'Tasks'
        }

        directory_name = type_mapping.get(object_type)
        if not directory_name:
            return None

        xml_file = self.config_path / directory_name / f"{object_name}.xml"

        if xml_file.exists():
            return xml_file

        return None

    def parse_information_register(self, xml_path: Path) -> Dict[str, Any]:
        """
        Parse InformationRegister XML metadata and convert to JSON structure.

        Args:
            xml_path: Path to the XML metadata file

        Returns:
            Dictionary representing the InformationRegister structure
        """
        tree = ET.parse(xml_path)
        root = tree.getroot()

        # Find the InformationRegister element (in default namespace)
        info_register = root.find('.//{http://v8.1c.ru/8.3/MDClasses}InformationRegister')
        if info_register is None:
            return {}

        properties = info_register.find('{http://v8.1c.ru/8.3/MDClasses}Properties')
        if properties is None:
            return {}

        # Extract basic properties
        name_elem = properties.find('{http://v8.1c.ru/8.3/MDClasses}Name')
        name = name_elem.text if name_elem is not None else ""

        synonym_elem = properties.find('.//{http://v8.1c.ru/8.1/data/core}content')
        synonym = synonym_elem.text if synonym_elem is not None else name

        periodicity_elem = properties.find('{http://v8.1c.ru/8.3/MDClasses}InformationRegisterPeriodicity')
        periodicity = periodicity_elem.text if periodicity_elem is not None else ""

        write_mode_elem = properties.find('{http://v8.1c.ru/8.3/MDClasses}WriteMode')
        write_mode = write_mode_elem.text if write_mode_elem is not None else ""

        # Parse dimensions
        dimensions = []
        child_objects = info_register.find('{http://v8.1c.ru/8.3/MDClasses}ChildObjects')
        if child_objects is not None:
            for dimension in child_objects.findall('{http://v8.1c.ru/8.3/MDClasses}Dimension'):
                dim_props = dimension.find('{http://v8.1c.ru/8.3/MDClasses}Properties')
                if dim_props is not None:
                    dim_name_elem = dim_props.find('{http://v8.1c.ru/8.3/MDClasses}Name')
                    dim_name = dim_name_elem.text if dim_name_elem is not None else ""

                    dim_synonym_elem = dim_props.find('.//{http://v8.1c.ru/8.1/data/core}content')
                    dim_synonym = dim_synonym_elem.text if dim_synonym_elem is not None else dim_name

                    # Parse type information
                    type_elem = dim_props.find('.//{http://v8.1c.ru/8.1/data/core}Type')
                    types = []
                    if type_elem is not None:
                        type_text = type_elem.text
                        if type_text and type_text.startswith('cfg:CatalogRef.'):
                            catalog_name = type_text.replace('cfg:CatalogRef.', '')
                            types.append({
                                "type": "Ref",
                                "id": f"Справочник.{catalog_name}"
                            })
                        elif type_text == 'xs:decimal':
                            # Look for number qualifiers
                            num_qual = dim_props.find('.//{http://v8.1c.ru/8.1/data/core}NumberQualifiers')
                            if num_qual is not None:
                                digits_elem = num_qual.find('{http://v8.1c.ru/8.1/data/core}Digits')
                                fraction_elem = num_qual.find('{http://v8.1c.ru/8.1/data/core}FractionDigits')
                                digits = digits_elem.text if digits_elem is not None else "10"
                                fraction = fraction_elem.text if fraction_elem is not None else "0"
                                types.append({
                                    "type": "Number",
                                    "NumberQualifiers": f"{digits}.{fraction}"
                                })

                    dimensions.append({
                        "id": dim_name,
                        "name": dim_synonym,
                        "types": types
                    })

        # Parse resources
        resources = []
        if child_objects is not None:
            for resource in child_objects.findall('{http://v8.1c.ru/8.3/MDClasses}Resource'):
                res_props = resource.find('{http://v8.1c.ru/8.3/MDClasses}Properties')
                if res_props is not None:
                    res_name_elem = res_props.find('{http://v8.1c.ru/8.3/MDClasses}Name')
                    res_name = res_name_elem.text if res_name_elem is not None else ""

                    res_synonym_elem = res_props.find('.//{http://v8.1c.ru/8.1/data/core}content')
                    res_synonym = res_synonym_elem.text if res_synonym_elem is not None else res_name

                    # Parse type information for resources
                    type_elem = res_props.find('.//{http://v8.1c.ru/8.1/data/core}Type')
                    types = []
                    if type_elem is not None:
                        type_text = type_elem.text
                        if type_text == 'xs:decimal':
                            # Look for number qualifiers
                            num_qual = res_props.find('.//{http://v8.1c.ru/8.1/data/core}NumberQualifiers')
                            if num_qual is not None:
                                digits_elem = num_qual.find('{http://v8.1c.ru/8.1/data/core}Digits')
                                fraction_elem = num_qual.find('{http://v8.1c.ru/8.1/data/core}FractionDigits')
                                digits = digits_elem.text if digits_elem is not None else "10"
                                fraction = fraction_elem.text if fraction_elem is not None else "0"
                                types.append({
                                    "type": "Number",
                                    "NumberQualifiers": f"{digits}.{fraction}"
                                })

                    resources.append({
                        "id": res_name,
                        "name": res_synonym,
                        "types": types
                    })

        return {
            "id": name,
            "name": synonym,
            "InformationRegisterPeriodicity": periodicity,
            "WriteMode": write_mode,
            "Dimensions": dimensions,
            "Resources": resources
        }

    def parse_catalog(self, xml_path: Path) -> Dict[str, Any]:
        """
        Parse Catalog XML metadata and convert to JSON structure.

        Args:
            xml_path: Path to the XML metadata file

        Returns:
            Dictionary representing the Catalog structure
        """
        tree = ET.parse(xml_path)
        root = tree.getroot()

        # Find the Catalog element (in default namespace)
        catalog = root.find('.//{http://v8.1c.ru/8.3/MDClasses}Catalog')
        if catalog is None:
            return {}

        properties = catalog.find('{http://v8.1c.ru/8.3/MDClasses}Properties')
        if properties is None:
            return {}

        # Extract basic properties
        name_elem = properties.find('{http://v8.1c.ru/8.3/MDClasses}Name')
        name = name_elem.text if name_elem is not None else ""

        synonym_elem = properties.find('.//{http://v8.1c.ru/8.1/data/core}content')
        synonym = synonym_elem.text if synonym_elem is not None else name

        # Parse attributes
        attributes = []
        child_objects = catalog.find('{http://v8.1c.ru/8.3/MDClasses}ChildObjects')
        if child_objects is not None:
            for attribute in child_objects.findall('{http://v8.1c.ru/8.3/MDClasses}Attribute'):
                attr_props = attribute.find('{http://v8.1c.ru/8.3/MDClasses}Properties')
                if attr_props is not None:
                    attr_name_elem = attr_props.find('{http://v8.1c.ru/8.3/MDClasses}Name')
                    attr_name = attr_name_elem.text if attr_name_elem is not None else ""

                    attr_synonym_elem = attr_props.find('.//{http://v8.1c.ru/8.1/data/core}content')
                    attr_synonym = attr_synonym_elem.text if attr_synonym_elem is not None else attr_name

                    # Parse type information
                    type_elem = attr_props.find('.//{http://v8.1c.ru/8.1/data/core}Type')
                    types = []
                    if type_elem is not None:
                        type_text = type_elem.text
                        if type_text:
                            if type_text.startswith('cfg:CatalogRef.'):
                                catalog_name = type_text.replace('cfg:CatalogRef.', '')
                                types.append({
                                    "type": "Ref",
                                    "id": f"Справочник.{catalog_name}"
                                })
                            elif type_text == 'xs:string':
                                # Look for string qualifiers
                                str_qual = attr_props.find('.//{http://v8.1c.ru/8.1/data/core}StringQualifiers')
                                if str_qual is not None:
                                    length_elem = str_qual.find('{http://v8.1c.ru/8.1/data/core}Length')
                                    length = length_elem.text if length_elem is not None else "0"
                                    types.append({
                                        "type": "String",
                                        "StringQualifiers": length
                                    })
                                else:
                                    types.append({"type": "String"})
                            elif type_text == 'xs:decimal':
                                # Look for number qualifiers
                                num_qual = attr_props.find('.//{http://v8.1c.ru/8.1/data/core}NumberQualifiers')
                                if num_qual is not None:
                                    digits_elem = num_qual.find('{http://v8.1c.ru/8.1/data/core}Digits')
                                    fraction_elem = num_qual.find('{http://v8.1c.ru/8.1/data/core}FractionDigits')
                                    digits = digits_elem.text if digits_elem is not None else "10"
                                    fraction = fraction_elem.text if fraction_elem is not None else "0"
                                    types.append({
                                        "type": "Number",
                                        "NumberQualifiers": f"{digits}.{fraction}"
                                    })
                                else:
                                    types.append({"type": "Number"})
                            elif type_text == 'xs:boolean':
                                types.append({"type": "Boolean"})
                            elif type_text == 'xs:dateTime':
                                types.append({"type": "Date"})

                    attributes.append({
                        "id": attr_name,
                        "name": attr_synonym,
                        "types": types
                    })

        # Parse tabular sections
        tabular_sections = []
        if child_objects is not None:
            for tab_section in child_objects.findall('{http://v8.1c.ru/8.3/MDClasses}TabularSection'):
                tab_props = tab_section.find('{http://v8.1c.ru/8.3/MDClasses}Properties')
                if tab_props is not None:
                    tab_name_elem = tab_props.find('{http://v8.1c.ru/8.3/MDClasses}Name')
                    tab_name = tab_name_elem.text if tab_name_elem is not None else ""

                    tab_synonym_elem = tab_props.find('.//{http://v8.1c.ru/8.1/data/core}content')
                    tab_synonym = tab_synonym_elem.text if tab_synonym_elem is not None else tab_name

                    # Parse tabular section attributes
                    tab_attributes = []
                    tab_child_objects = tab_section.find('{http://v8.1c.ru/8.3/MDClasses}ChildObjects')
                    if tab_child_objects is not None:
                        for tab_attr in tab_child_objects.findall('{http://v8.1c.ru/8.3/MDClasses}Attribute'):
                            tab_attr_props = tab_attr.find('{http://v8.1c.ru/8.3/MDClasses}Properties')
                            if tab_attr_props is not None:
                                tab_attr_name_elem = tab_attr_props.find('{http://v8.1c.ru/8.3/MDClasses}Name')
                                tab_attr_name = tab_attr_name_elem.text if tab_attr_name_elem is not None else ""

                                tab_attr_synonym_elem = tab_attr_props.find('.//{http://v8.1c.ru/8.1/data/core}content')
                                tab_attr_synonym = tab_attr_synonym_elem.text if tab_attr_synonym_elem is not None else tab_attr_name

                                # Parse type information for tabular section attributes
                                tab_type_elem = tab_attr_props.find('.//{http://v8.1c.ru/8.1/data/core}Type')
                                tab_types = []
                                if tab_type_elem is not None:
                                    tab_type_text = tab_type_elem.text
                                    if tab_type_text:
                                        if tab_type_text.startswith('cfg:CatalogRef.'):
                                            catalog_name = tab_type_text.replace('cfg:CatalogRef.', '')
                                            tab_types.append({
                                                "type": "Ref",
                                                "id": f"Справочник.{catalog_name}"
                                            })
                                        elif tab_type_text == 'xs:string':
                                            str_qual = tab_attr_props.find('.//{http://v8.1c.ru/8.1/data/core}StringQualifiers')
                                            if str_qual is not None:
                                                length_elem = str_qual.find('{http://v8.1c.ru/8.1/data/core}Length')
                                                length = length_elem.text if length_elem is not None else "0"
                                                tab_types.append({
                                                    "type": "String",
                                                    "StringQualifiers": length
                                                })
                                            else:
                                                tab_types.append({"type": "String"})
                                        elif tab_type_text == 'xs:decimal':
                                            num_qual = tab_attr_props.find('.//{http://v8.1c.ru/8.1/data/core}NumberQualifiers')
                                            if num_qual is not None:
                                                digits_elem = num_qual.find('{http://v8.1c.ru/8.1/data/core}Digits')
                                                fraction_elem = num_qual.find('{http://v8.1c.ru/8.1/data/core}FractionDigits')
                                                digits = digits_elem.text if digits_elem is not None else "10"
                                                fraction = fraction_elem.text if fraction_elem is not None else "0"
                                                tab_types.append({
                                                    "type": "Number",
                                                    "NumberQualifiers": f"{digits}.{fraction}"
                                                })
                                            else:
                                                tab_types.append({"type": "Number"})

                                tab_attributes.append({
                                    "id": tab_attr_name,
                                    "name": tab_attr_synonym,
                                    "types": tab_types
                                })

                    tabular_sections.append({
                        "id": tab_name,
                        "name": tab_synonym,
                        "Attributes": tab_attributes
                    })

        result = {
            "id": name,
            "name": synonym,
            "Attributes": attributes
        }

        if tabular_sections:
            result["TabularSections"] = tabular_sections

        return result

    def parse_accumulation_register(self, xml_path: Path) -> Dict[str, Any]:
        """
        Parse AccumulationRegister XML metadata and convert to JSON structure.

        Args:
            xml_path: Path to the XML metadata file

        Returns:
            Dictionary representing the AccumulationRegister structure
        """
        tree = ET.parse(xml_path)
        root = tree.getroot()

        # Find the AccumulationRegister element (in default namespace)
        acc_register = root.find('.//{http://v8.1c.ru/8.3/MDClasses}AccumulationRegister')
        if acc_register is None:
            return {}

        properties = acc_register.find('{http://v8.1c.ru/8.3/MDClasses}Properties')
        if properties is None:
            return {}

        # Extract basic properties
        name_elem = properties.find('{http://v8.1c.ru/8.3/MDClasses}Name')
        name = name_elem.text if name_elem is not None else ""

        synonym_elem = properties.find('.//{http://v8.1c.ru/8.1/data/core}content')
        synonym = synonym_elem.text if synonym_elem is not None else name

        register_type_elem = properties.find('{http://v8.1c.ru/8.3/MDClasses}RegisterType')
        register_type = register_type_elem.text if register_type_elem is not None else ""

        # Parse dimensions
        dimensions = []
        child_objects = acc_register.find('{http://v8.1c.ru/8.3/MDClasses}ChildObjects')
        if child_objects is not None:
            for dimension in child_objects.findall('{http://v8.1c.ru/8.3/MDClasses}Dimension'):
                dim_props = dimension.find('{http://v8.1c.ru/8.3/MDClasses}Properties')
                if dim_props is not None:
                    dim_name_elem = dim_props.find('{http://v8.1c.ru/8.3/MDClasses}Name')
                    dim_name = dim_name_elem.text if dim_name_elem is not None else ""

                    dim_synonym_elem = dim_props.find('.//{http://v8.1c.ru/8.1/data/core}content')
                    dim_synonym = dim_synonym_elem.text if dim_synonym_elem is not None else dim_name

                    # Parse type information
                    type_elem = dim_props.find('.//{http://v8.1c.ru/8.1/data/core}Type')
                    types = []
                    if type_elem is not None:
                        type_text = type_elem.text
                        if type_text and type_text.startswith('cfg:CatalogRef.'):
                            catalog_name = type_text.replace('cfg:CatalogRef.', '')
                            types.append({
                                "type": "Ref",
                                "id": f"Справочник.{catalog_name}"
                            })
                        elif type_text == 'xs:decimal':
                            # Look for number qualifiers
                            num_qual = dim_props.find('.//{http://v8.1c.ru/8.1/data/core}NumberQualifiers')
                            if num_qual is not None:
                                digits_elem = num_qual.find('{http://v8.1c.ru/8.1/data/core}Digits')
                                fraction_elem = num_qual.find('{http://v8.1c.ru/8.1/data/core}FractionDigits')
                                digits = digits_elem.text if digits_elem is not None else "10"
                                fraction = fraction_elem.text if fraction_elem is not None else "0"
                                types.append({
                                    "type": "Number",
                                    "NumberQualifiers": f"{digits}.{fraction}"
                                })

                    dimensions.append({
                        "id": dim_name,
                        "name": dim_synonym,
                        "types": types
                    })

        # Parse resources
        resources = []
        if child_objects is not None:
            for resource in child_objects.findall('{http://v8.1c.ru/8.3/MDClasses}Resource'):
                res_props = resource.find('{http://v8.1c.ru/8.3/MDClasses}Properties')
                if res_props is not None:
                    res_name_elem = res_props.find('{http://v8.1c.ru/8.3/MDClasses}Name')
                    res_name = res_name_elem.text if res_name_elem is not None else ""

                    res_synonym_elem = res_props.find('.//{http://v8.1c.ru/8.1/data/core}content')
                    res_synonym = res_synonym_elem.text if res_synonym_elem is not None else res_name

                    # Parse type information for resources
                    type_elem = res_props.find('.//{http://v8.1c.ru/8.1/data/core}Type')
                    types = []
                    if type_elem is not None:
                        type_text = type_elem.text
                        if type_text == 'xs:decimal':
                            # Look for number qualifiers
                            num_qual = res_props.find('.//{http://v8.1c.ru/8.1/data/core}NumberQualifiers')
                            if num_qual is not None:
                                digits_elem = num_qual.find('{http://v8.1c.ru/8.1/data/core}Digits')
                                fraction_elem = num_qual.find('{http://v8.1c.ru/8.1/data/core}FractionDigits')
                                digits = digits_elem.text if digits_elem is not None else "10"
                                fraction = fraction_elem.text if fraction_elem is not None else "0"
                                types.append({
                                    "type": "Number",
                                    "NumberQualifiers": f"{digits}.{fraction}"
                                })

                    resources.append({
                        "id": res_name,
                        "name": res_synonym,
                        "types": types
                    })

        return {
            "id": name,
            "name": synonym,
            "RegisterType": register_type,
            "Dimensions": dimensions,
            "Resources": resources
        }

    def convert_identifiers_to_json(self, identifiers: List[str]) -> Dict[str, Any]:
        """
        Convert a list of 1C identifiers to JSON representation.

        Args:
            identifiers: List of 1C identifiers like ["РегистрСведений.ЦеныТоваров"]

        Returns:
            Dictionary with the JSON representation
        """
        result = {}

        for identifier in identifiers:
            object_type, object_name = self.parse_identifier(identifier)

            if object_type == "РегистрСведений":
                xml_path = self.get_metadata_file_path(object_type, object_name)
                if xml_path:
                    info_register_data = self.parse_information_register(xml_path)
                    if info_register_data:
                        if "InformationRegisters" not in result:
                            result["InformationRegisters"] = []
                        result["InformationRegisters"].append(info_register_data)

            elif object_type == "Справочник":
                xml_path = self.get_metadata_file_path(object_type, object_name)
                if xml_path:
                    catalog_data = self.parse_catalog(xml_path)
                    if catalog_data:
                        if "Catalogs" not in result:
                            result["Catalogs"] = []
                        result["Catalogs"].append(catalog_data)

            elif object_type == "РегистрНакопления":
                xml_path = self.get_metadata_file_path(object_type, object_name)
                if xml_path:
                    acc_register_data = self.parse_accumulation_register(xml_path)
                    if acc_register_data:
                        if "AccumulationRegisters" not in result:
                            result["AccumulationRegisters"] = []
                        result["AccumulationRegisters"].append(acc_register_data)

        return result

    def save_to_file(self, data: Dict[str, Any], output_path: str) -> None:
        """
        Save the JSON data to a file.

        Args:
            data: Dictionary to save as JSON
            output_path: Path to save the JSON file
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    """Example usage of the C1ContextBuilder class."""
    builder = C1ContextBuilder()

    # Example: Convert the identifier from the task
    # identifiers = ["РегистрСведений.ЦеныТоваров", "Справочник.Товары"]
    identifiers = ["РегистрСведений.ПериодыРемонтаСкладов"]
    # identifiers = ["РегистрНакопления.ТоварныеЗапасы"]
    # identifiers = ["Справочник.ИсходящиеПисьма"]

    result = builder.convert_identifiers_to_json(identifiers)

    # Save to the expected output file
    output_path = r"C:\Work\projects\sberdevices\dev\1cbench\bench-dev\task_space\task_019_context.json"
    builder.save_to_file(result, output_path)

    print(f"Context JSON saved to: {output_path}")
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()