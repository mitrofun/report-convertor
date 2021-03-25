import os
from datetime import datetime
from typing import List, Optional
from xml.etree import ElementTree

from openpyxl import load_workbook, worksheet
from loguru import logger

from pydantic import BaseModel, validator, Field
from pydantic import parse_obj_as

import vkbeautify as vkb


class XMLModel(BaseModel):
    year: int = Field(name='Год')
    inn: int = Field(name='ИНН')
    kpp: int = Field(name='КПП')

    @validator('*')
    def set_value(cls, value):
        return value or 0

    @staticmethod
    def exclude_fields() -> List[str]:
        """Fields exclude for xml report.Not used."""
        return []

    @staticmethod
    def display_value(value):
        if type(value) == str:
            return value
        return str(value) if type(value) == int else '%.2f' % value

    def represent_to_xml(self):
        """Represent for xml report"""
        properties = self.schema()['properties']
        return dict((properties[key]['name'], self.display_value(value)) for (key, value) in self.dict().items()
                    if key not in self.exclude_fields()).items()


class Accrual(BaseModel):
    """
    Row from report in first sheet
    """
    year: int
    month: int
    inn: int
    kpp: int
    okfs: int
    org_type: str
    employee_name: str
    snils: int
    work_experience: int
    position: str
    staff_category_code: int
    employment_conditions: str
    bid: float
    number_working_hours_according: float
    actual_time_worked: float
    accruals_based_on_tariff_rates: float
    hazard_class: int
    accruals_for_hazard_class: float
    additional_payment_for_combining: float
    other_compensation_payments: float
    other_compensation_payments_regional: float
    awards: float
    experience_for_additional_payments: str
    payment_for_work_experience: float
    rural_surcharge: float
    qualification_category: str
    additional_payment_for_presence_of_qualifying_category: float
    academic_degree: str
    additional_payment_for_academic_degree: float
    additional_payment_for_mentoring: float
    additional_payment_young_specialists: float
    other_additional_payment: float
    other_payments: float
    compensation_payments_for_district_regulation: float
    total_accruals: float


class Employee(BaseModel):
    """
    All employee accrual.Group by employee for xml export
    """
    snils: int
    full_name: str
    first_name: str
    middle_name: str
    last_name: str
    accruals: List[Accrual]


class SalaryFund(XMLModel):
    """
    Row from report from second sheet
    """
    okogu: int = Field(name='ОКОГУ')
    federal_budget_total: Optional[float] = Field(name='РасхОбщФед')
    federal_budget_category: Optional[float] = Field(name='РасхКатФед')
    municipal_budget_total: Optional[float] = Field(name='РасхОбщСуб')
    municipal_budget_category: Optional[float] = Field(name='РасхКатСуб')
    medical_budget_total: Optional[float] = Field(name='РасхОбщМун')
    medical_budget_category: Optional[float] = Field(name='РасхКатМун')
    other_budget_total: Optional[float] = Field(name='РасхОбщОМС')
    other_budget_category: Optional[float] = Field(name='РасхКатОМС')

    def exclude_fields(self) -> List[str]:
        return ['inn', 'kpp', 'okogu']


class ExecutiveSalary(XMLModel):
    """
    Row from report from third sheet
    """
    average_executive_salary: Optional[float] = Field(name='СредЗПРук')
    average_salary_of_deputy_manager: Optional[float] = Field(name='СредЗПЗам')
    average_salary_of_chief_accountant: Optional[float] = Field(name='СредЗПГлБух')
    average_salary_of_employees: Optional[float] = Field(name='РасхОбщФед')

    def exclude_fields(self) -> List[str]:
        return ['inn', 'kpp']


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


def load_salary_info(ws: worksheet) -> None:
    pass


def _load_salary_fund(ws: worksheet) -> List[SalaryFund]:
    values = _get_value_list(ws.rows, 4)
    dict_values = _create_list_of_dict_values_for_model(SalaryFund, values)
    return parse_obj_as(List[SalaryFund], dict_values)


def _load_executive_salaries(ws: worksheet) -> List[ExecutiveSalary]:
    values = _get_value_list(ws.rows, 3)
    dict_values = _create_list_of_dict_values_for_model(ExecutiveSalary, values)
    return parse_obj_as(List[ExecutiveSalary], dict_values)


def add_child_nodes(parent_node, data: List[dict]) -> None:
    for item in data:
        child_node = ElementTree.SubElement(parent_node, "Период")
        for key, value in item.represent_to_xml():
            node = ElementTree.SubElement(child_node, key)
            node.text = value


def add_salary_fond_node(root_node, data) -> None:
    parent_node = ElementTree.SubElement(root_node, "ФондЗП")
    add_child_nodes(parent_node, data)


def add_executive_salary_node(root_node, data) -> None:
    parent_node = ElementTree.SubElement(root_node, "СЗПРук")
    add_child_nodes(parent_node, data)


def create_xml_file(temp_filename, filename, salary_fund_data, executive_salary):
    root = ElementTree.Element("ЭДПФР", xmlns='http://пф.рф/СИоЗП/2021-03-15')
    root.set('xmlns:УТ2', 'http://пф.рф/УТ/2017-08-21')
    root.set('xmlns:АФ5', 'http://пф.рф/АФ/2018-12-07')
    main_node = ElementTree.Element('СИоЗП')
    root.append(main_node)

    # Salary found 2 part
    add_salary_fond_node(main_node, salary_fund_data)
    # 3 part
    add_executive_salary_node(main_node, executive_salary)

    tree = ElementTree.ElementTree(root)

    tree.write(temp_filename, encoding='utf-8', xml_declaration=True)
    vkb.xml(temp_filename, filename)


def main(base_dir: str):
    """
    Read xlsx file from input folder and create xml report for the pension fund in folder output
    :param base_dir: str - current working directory
    :return: None
    """
    logger.info('Start load data')

    temp_xml_file = os.path.join(base_dir, 'output', 'temp.xml')
    xml_file = os.path.join(base_dir, 'output', f'{datetime.now().strftime("%Y-%m-%d-%H-%M-%S")}.xml')

    wb = load_workbook(filename=os.path.join(base_dir, 'input', 'example.xlsx'), read_only=True)
    # load_salary_info(wb['Раздел 1'])
    salary_fund_data = _load_salary_fund(wb['Раздел 2'])
    executive_salary = _load_executive_salaries(wb['Раздел 3'])
    logger.debug(f'create salary_fund: {salary_fund_data}\ncreate executive_salary: {executive_salary}\n')
    wb.close()
    logger.info('Generate xml file')
    create_xml_file(temp_xml_file, xml_file, salary_fund_data, executive_salary)
    os.remove(temp_xml_file)
    logger.info('Complete generate xml file')


if __name__ == '__main__':
    main(os.getcwd())
