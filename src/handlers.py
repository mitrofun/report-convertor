from datetime import datetime
from typing import List, Any
from xml.etree import ElementTree
from xml.dom.minidom import parseString


from openpyxl import worksheet
from loguru import logger
from pydantic import (
    ValidationError,
    parse_obj_as,
)

from src.models import Salary, SalaryFund, ExecutiveSalary, Period, Employee
from src.settings import Settings


settings = Settings()


def _create_list_of_dict_values_for_model(model, list_of_values: List[List]) -> List[dict]:
    result = []
    fields = model.__fields__.keys()
    for item in list_of_values:
        result.append(dict(zip(fields, item)))
    return result


def _get_value_list(rows, for_row: int) -> List[List[int or float or None]]:
    values = []
    for i, row in enumerate(rows):
        if i >= for_row:
            row_values = []
            for cell in row:
                row_values.append(cell.value)
            values.append(row_values)
    return values


def _add_child_nodes(parent_node, data: List[Any]) -> None:
    for item in data:
        child_node = ElementTree.SubElement(parent_node, 'Период')
        for key, value in item.represent_to_xml():
            node = ElementTree.SubElement(child_node, key)
            node.text = value


def _add_period_nodes(parent_node, data: List[Any]) -> None:
    for item in data:
        child_node = ElementTree.SubElement(parent_node, 'Период')
        sub_nodes = ElementTree.SubElement(child_node, 'ОтчетныйПериод')
        for key, value in item.represent_to_xml():
            node = ElementTree.SubElement(sub_nodes, key)
            node.text = value
        parent_employee_node = ElementTree.SubElement(child_node, 'Работник')
        for employee in item.employee:

            if employee.salary:
                employee_node = ElementTree.SubElement(parent_employee_node, 'УТ2:ФИО')
                for key, value in employee.represent_name_to_xml():
                    node = ElementTree.SubElement(employee_node, key)
                    node.text = value
                node = ElementTree.SubElement(parent_employee_node, 'УТ2:СНИЛС')
                node.text = str(employee.snils)
                node = ElementTree.SubElement(parent_employee_node, 'ОбщийСтаж')
                node.text = str(employee.work_experience)
                for salary_item in employee.salary:
                    salary_root_node = ElementTree.SubElement(parent_employee_node, 'СЗПД')

                    for key, value in salary_item.represent_to_xml():
                        node = ElementTree.SubElement(salary_root_node, key)
                        node.text = value


def _add_organization_node(root_node, salary_data: List, fund_data: List) -> None:
    parent_node = ElementTree.SubElement(root_node, 'Организация')
    for key, value in salary_data[0].represent_organization_to_xml():
        node = ElementTree.SubElement(parent_node, key)
        node.text = value
    for key, value in fund_data[0].represent_organization_to_xml():
        node = ElementTree.SubElement(parent_node, key)
        node.text = value


def _add_salary_node(root_node, data) -> None:
    parent_node = ElementTree.SubElement(root_node, 'СЗП')
    _add_period_nodes(parent_node, data)


def _add_salary_fond_node(root_node, data) -> None:
    parent_node = ElementTree.SubElement(root_node, 'ФондЗП')
    _add_child_nodes(parent_node, data)


def _add_executive_salary_node(root_node, data) -> None:
    parent_node = ElementTree.SubElement(root_node, 'СЗПРук')
    _add_child_nodes(parent_node, data)


def _add_system_node(root_node, guid) -> None:
    parent_node = ElementTree.SubElement(root_node, 'СлужебнаяИнформация')
    node = ElementTree.SubElement(parent_node, 'АФ5:GUID')
    node.text = guid
    node = ElementTree.SubElement(parent_node, 'АФ5:ДатаВремя')
    node.text = datetime.now().isoformat()


def create_xml_file(filename, salary_data, salary_fund_data, executive_salary, guid, salary_emp_data):
    root = ElementTree.Element('ЭДПФР', xmlns='http://пф.рф/СИоЗП/2021-03-15')
    root.set('xmlns:УТ2', 'http://пф.рф/УТ/2017-08-21')
    root.set('xmlns:АФ5', 'http://пф.рф/АФ/2018-12-07')
    main_node = ElementTree.Element('СИоЗП')
    root.append(main_node)
    # Organization info
    _add_organization_node(main_node, salary_emp_data, salary_fund_data)
    # 1 part
    _add_salary_node(main_node, salary_data)
    # Salary found 2 part
    _add_salary_fond_node(main_node, salary_fund_data)
    # 3 part
    _add_executive_salary_node(main_node, executive_salary)
    # system info
    _add_system_node(main_node, guid)
    # for pretty file without minification
    # if not need pretty
    #
    # code:
    # tree = ElementTree.ElementTree(root)
    # tree.write(filename, encoding='utf-8', xml_declaration=True)
    #
    # And delete code further in function
    xml_string = ElementTree.tostring(
        root, encoding='utf-8', method='xml', xml_declaration=True, short_empty_elements=True)
    xml = parseString(xml_string)
    xml_pretty_str = xml.toprettyxml(encoding='utf-8')
    with open(filename, mode='wb') as result:
        result.write(xml_pretty_str)


def _create_list_with_instances_from_salary_data(instance, salary_data, fields: List):
    # for Period
    if len(fields) == 2:
        unique_values = list(set(list(map(lambda item: (item.dict()[fields[0]], item.dict()[fields[1]]), salary_data))))
    else:
        # for Employee
        unique_values = list(set(list(
            map(lambda item: (item.dict()[fields[0]], item.dict()[fields[1]], item.dict()[fields[2]]), salary_data))))
    unique_values.sort(key=lambda x: x[1])
    source = _create_list_of_dict_values_for_model(instance, unique_values)
    return parse_obj_as(List[instance], source)


def load_salary(ws: worksheet) -> List[Salary]:
    values = _get_value_list(ws.rows, 5)
    dict_values = _create_list_of_dict_values_for_model(Salary, values)
    try:
        return parse_obj_as(List[Salary], dict_values)
    except ValidationError as e:
        logger.error(e)


def load_salary_fund(ws: worksheet) -> List[SalaryFund]:
    values = _get_value_list(ws.rows, 4)
    dict_values = _create_list_of_dict_values_for_model(SalaryFund, values)
    return parse_obj_as(List[SalaryFund], dict_values)


def load_executive_salaries(ws: worksheet) -> List[ExecutiveSalary]:
    values = _get_value_list(ws.rows, 3)
    dict_values = _create_list_of_dict_values_for_model(ExecutiveSalary, values)
    return parse_obj_as(List[ExecutiveSalary], dict_values)


def create_group_by_period_salary_data(salary_data) -> List[Period]:
    periods = _create_list_with_instances_from_salary_data(Period, salary_data, ['year', 'month'])
    # add employees to period
    for item in periods:
        employees = _create_list_with_instances_from_salary_data(
            Employee,
            salary_data,
            ['snils', 'employee_name', 'work_experience'],
        )
        item.employee = employees
    # add salary for employee in equal period
    for period_item in periods:
        for employee in period_item.employee:
            for salary_item in salary_data:

                is_equal_year = salary_item.year == period_item.year
                is_equal_month = salary_item.month == period_item.month
                is_equal_snils = employee.snils == salary_item.snils

                if is_equal_year and is_equal_month and is_equal_snils:
                    employee.salary.append(salary_item)
    return periods
