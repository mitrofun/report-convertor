import os
import uuid
from enum import Enum
from datetime import datetime
from typing import List, Optional
from xml.etree import ElementTree

from dateparser import DateDataParser
from openpyxl import load_workbook, worksheet
from loguru import logger
from pydantic import BaseModel, BaseSettings, Field, validator, parse_obj_as, ValidationError, root_validator
import vkbeautify as vkb


logger.add("report.log", enqueue=True)

ALLOW_CATEGORY_CODE = (201, 221, 291, 211, 232, 233, 242, 243, 261, 401, 431, 411, 421, 501, 311, 281, 100, 600,)


class Settings(BaseSettings):
    report: str = 'example.xlsx'
    input_dir: str = './input'
    output_dir: str = './output'
    code_to: str
    reg_number: str

    class Config:
        env_file = 'config.env'


class IndexEnum(Enum):
    def __new__(cls, *args):
        counter = len(cls.__members__) + 1
        obj = object.__new__(cls)
        obj.index = counter
        return obj


class EmploymentCondition(IndexEnum):
    MAIN = 'Основное'
    EXTERNAL = 'Внешнее совместительство'
    INTERNAL = 'Внутреннее совместительство'


class QualificationCategory(IndexEnum):
    FIRST = 'первая'
    SECOND = 'вторая'
    HIGHER = 'высшая'


class AcademicDegree(IndexEnum):
    CANDIDATE = 'кандидат наук'
    DOCTOR = 'доктор наук'


class XMLBaseModel(BaseModel):

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
        """Represent for xml report.Exclude dont need fields"""
        properties = self.schema()['properties']
        return dict((properties[key]['name'], self.display_value(value)) for (key, value) in self.dict().items()
                    if key not in self.exclude_fields()).items()


class OrgBaseModel(XMLBaseModel):
    year: int = Field(name='Год')
    inn: int = Field(name='ИНН')
    kpp: int = Field(name='КПП')


def get_mount_number(name: str) -> int:
    """
    Get month number by name
    Use `dateparser` for cross-platform solution. Develop on Mac os, use on Windows
    Because native solution have different name in module calendar, for example
    on Windows `Январь` on Mac Os `января`
    """
    ddp = DateDataParser(languages=['ru'])
    date_data = ddp.get_date_data(f'1 {name}')
    return date_data.date_obj.month


def is_value_len(length) -> bool:
    if len(str(length)) == length:
        return True
    return False


def convert_experience(value: str) -> str:
    """
    Convert input value `XX лет XX мес` to `XX.XX`.
    Not check month value less 12.
    """
    replaced_value: str = value.replace('лет', '.').replace('мес', '').replace(' ', '')
    years, months = replaced_value.split('.')
    return f'{years.zfill(2)}.{months.zfill(2)}'


class Salary(XMLBaseModel):
    """
    Row from report in first sheet
    """
    year: int = Field(name='Год')
    month: int = Field(name='Месяц')
    inn: str = Field(name='УТ2:ИНН', min_length=10, max_length=10)
    kpp: str = Field(name='УТ2:КПП', min_length=9, max_length=9)
    okfs: int = Field(name='ОКФС', ge=12, le=14)
    org_type: str = Field(name='КТО')
    employee_name: str = Field(name='УТ2:ФИО')
    snils: int = Field(name='УТ2:СНИЛС')
    work_experience: int = Field(name='ОбщийСтаж')
    position: str = Field(name='Должность')
    staff_category_code: int = Field(600, name='ККП')
    employment_conditions: str = Field(name='УсловиеЗанятости')
    bid: float = Field(name='Ставка', le=1, ge=0)
    number_working_hours_according: float = Field(name='РабВремяНорма', ge=0)
    actual_time_worked: float = Field(name='РабВремяФакт', ge=0)
    accruals_based_on_tariff_rates: Optional[float] = Field(name='НачисленияТариф')
    hazard_class: Optional[int] = Field(name='ОУТ')
    accruals_for_hazard_class: Optional[float] = Field(name='НачисленияОУТ')
    additional_payment_for_combining: Optional[float] = Field(name='ДоплатаСовмещение')
    other_compensation_payments: Optional[float] = Field(name='НачисленияИныеФед')
    other_compensation_payments_regional: Optional[float] = Field(name='НачисленияИныеРег')
    awards: Optional[float] = Field(name='НачисленияПремии')
    experience_for_additional_payments: str = Field(name='НепрерывныйСтаж')
    payment_for_work_experience: Optional[float] = Field(name='ДоплатаСтаж')
    rural_surcharge: Optional[float] = Field(name='ДоплатаСМ')
    qualification_category: Optional[str] = Field(name='КвалКатегория')
    additional_payment_for_presence_of_qualifying_category: Optional[float] = Field(name='ДоплатаКвалКат')
    academic_degree: Optional[str] = Field(name='УченаяСтепень')
    additional_payment_for_academic_degree: Optional[float] = Field(name='ДоплатаУС')
    additional_payment_for_mentoring: Optional[float] = Field(name='ДоплатаНаставничество')
    additional_payment_young_specialists: Optional[float] = Field(name='ДоплатаМолодСпец')
    other_additional_payment: Optional[float] = Field(name='ВыплатыИныеСтимул')
    other_payments: Optional[float] = Field(0, name='ВыплатыПрочие')
    compensation_payments_for_district_regulation: Optional[float] = Field(0, name='ВыплатыКомпенс')
    total_accruals: Optional[float] = Field(0, name='НачисленияИтого')

    def exclude_fields(self) -> List[str]:
        return ['inn', 'kpp', 'okfs', 'org_type', 'employee_name', 'snils', 'work_experience']

    @validator('month', pre=True)
    def prepare_month(cls, v):
        if type(v) == int:
            return v
        return get_mount_number(v)

    @validator('staff_category_code')
    def check_code(cls, v):
        if v not in ALLOW_CATEGORY_CODE:
            logger.error(f'Error in staff category code: {v}.Allow values only {ALLOW_CATEGORY_CODE}.')
            raise ValueError('Проверьте категорию персонала')
        return v

    @validator('experience_for_additional_payments', pre=True)
    def convert_value(cls, v):
        return convert_experience(v)

    @validator('employment_conditions', pre=True)
    def change_employment_conditions(cls, v):
        if not v:
            return
        return EmploymentCondition(v).index

    @validator('qualification_category', pre=True)
    def change_qualification_category(cls, v):
        if not v:
            return
        return QualificationCategory(v).index

    @validator('academic_degree', pre=True)
    def change_academic_degree(cls, v):
        if not v:
            return
        return AcademicDegree(v).index

    def represent_organization_to_xml(self):
        """Represent for xml report for organization node"""
        fields = ['inn', 'kpp', 'okfs', 'org_type']
        properties = self.schema()['properties']
        return dict((properties[key]['name'], self.display_value(value)) for (key, value) in self.dict().items()
                    if key in fields).items()


def decompose_full_name(full_name: str) -> List[str]:
    result = full_name.split(' ')
    if len(result) == 4:
        return [result[0], result[1], f'{result[2]} {result[3]}']
    if len(result) == 2:
        result.append('')
        return result
    return result


class Employee(XMLBaseModel):
    """
    All employee accrual.Group by employee for xml export
    """
    snils: int = Field(name='УТ2:СНИЛС')
    full_name: str = Field(name='РасхОбщФед')
    work_experience: int = Field(name='ОбщийСтаж')
    first_name: Optional[str] = Field(name='УТ2:Имя')
    middle_name: Optional[str] = Field(name='УТ2:Отчество')
    last_name: Optional[str] = Field(name='УТ2:Фамилия')
    salary: Optional[List[Salary]] = Field([])

    @root_validator(pre=True)
    def fill_names(cls, values):
        full_name = values['full_name']
        last_name, first_name, middle_name = decompose_full_name(full_name)
        return {'first_name': first_name, 'last_name': last_name, 'middle_name': middle_name, **values}

    def represent_name_to_xml(self):
        """Represent for xml report"""
        properties = self.schema()['properties']
        fields = ['last_name', 'first_name', 'middle_name', ]
        return dict((properties[key]['name'], self.display_value(value)) for (key, value) in self.dict().items()
                    if key in fields).items()


class Period(XMLBaseModel):
    """
    Period for group data.
    Note: To group by organization, you need to use another level.
    We make an assumption - one report file-one organization.
    """
    year: int = Field(name='Год')
    month: int = Field(name='Месяц')
    employee: Optional[Employee]

    def exclude_fields(self) -> List[str]:
        return ['employee']


class SalaryFund(OrgBaseModel):
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

    def represent_organization_to_xml(self):
        """Represent for xml report for organization node"""
        fields = ['okogu']
        properties = self.schema()['properties']
        return dict((properties[key]['name'], self.display_value(value)) for (key, value) in self.dict().items()
                    if key in fields).items()


class ExecutiveSalary(OrgBaseModel):
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


def _load_salary(ws: worksheet) -> List[Salary]:
    values = _get_value_list(ws.rows, 5)
    dict_values = _create_list_of_dict_values_for_model(Salary, values)
    try:
        return parse_obj_as(List[Salary], dict_values)
    except ValidationError as e:
        logger.error(e)


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
        child_node = ElementTree.SubElement(parent_node, 'Период')
        for key, value in item.represent_to_xml():
            node = ElementTree.SubElement(child_node, key)
            node.text = value


def add_period_nodes(parent_node, data: List[dict]) -> None:
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


def add_organization_node(root_node, salary_data: List, fund_data: List) -> None:
    parent_node = ElementTree.SubElement(root_node, 'Организация')
    for key, value in salary_data[0].represent_organization_to_xml():
        node = ElementTree.SubElement(parent_node, key)
        node.text = value
    for key, value in fund_data[0].represent_organization_to_xml():
        node = ElementTree.SubElement(parent_node, key)
        node.text = value


def add_salary_node(root_node, data) -> None:
    parent_node = ElementTree.SubElement(root_node, 'СЗП')
    add_period_nodes(parent_node, data)


def add_salary_fond_node(root_node, data) -> None:
    parent_node = ElementTree.SubElement(root_node, 'ФондЗП')
    add_child_nodes(parent_node, data)


def add_executive_salary_node(root_node, data) -> None:
    parent_node = ElementTree.SubElement(root_node, 'СЗПРук')
    add_child_nodes(parent_node, data)


def add_system_node(root_node, guid) -> None:
    parent_node = ElementTree.SubElement(root_node, 'СлужебнаяИнформация')
    node = ElementTree.SubElement(parent_node, 'АФ5:GUID')
    node.text = guid
    node = ElementTree.SubElement(parent_node, 'АФ5:ДатаВремя')
    node.text = datetime.now().isoformat()


def create_xml_file(temp_filename, filename, salary_data, salary_fund_data, executive_salary, guid, salary_emp_data):
    root = ElementTree.Element('ЭДПФР', xmlns='http://пф.рф/СИоЗП/2021-03-15')
    root.set('xmlns:УТ2', 'http://пф.рф/УТ/2017-08-21')
    root.set('xmlns:АФ5', 'http://пф.рф/АФ/2018-12-07')
    main_node = ElementTree.Element('СИоЗП')
    root.append(main_node)
    # Organization info
    add_organization_node(main_node, salary_emp_data, salary_fund_data)
    # 1 part
    add_salary_node(main_node, salary_data)
    # Salary found 2 part
    add_salary_fond_node(main_node, salary_fund_data)
    # 3 part
    add_executive_salary_node(main_node, executive_salary)
    # system info
    add_system_node(main_node, guid)
    tree = ElementTree.ElementTree(root)

    tree.write(temp_filename, encoding='utf-8', xml_declaration=True)
    vkb.xml(temp_filename, filename)


def delete_file(filename: str) -> None:
    """Delete file if exist"""
    if os.path.exists(filename):
        os.remove(filename)


def create_group_by_period_salary_data(salary_data) -> List[Period]:
    periods = _create_list_with_instances_from_salary_data(Period, salary_data, ['year', 'month'])
    # add employees to period
    for item in periods:
        employees = _create_list_with_instances_from_salary_data(
            Employee,
            salary_data,
            ['snils', 'employee_name', 'work_experience']
        )
        item.employee = employees
    # add salary for employee in equal period
    for period_item in periods:
        for employee in period_item.employee:
            for salary_item in salary_data:
                if (
                        salary_item.year == period_item.year and
                        salary_item.month == period_item.month and
                        employee.snils == salary_item.snils
                ):
                    employee.salary.append(salary_item)
    return periods


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


def main(base_dir: str):
    """
    Read xlsx file from input folder and create xml report for the pension fund in folder output
    :param base_dir: str - current working directory
    :return: None
    """
    logger.info('Start load data')
    guid: str = str(uuid.uuid4())
    settings = Settings()
    temp_xml_file = os.path.join(base_dir, settings.output_dir, 'temp.xml')
    file_name = f'ПФР_{settings.code_to}_СИоЗП_{settings.reg_number}_{datetime.now().strftime("%Y%m%d")}_{guid}.xml'
    xml_file = os.path.join(base_dir, settings.output_dir, file_name)
    report_file = os.path.join(base_dir, settings.input_dir, settings.report)
    logger.info(f'Read file: {report_file}')
    wb = load_workbook(filename=report_file, read_only=True)
    salary_data = _load_salary(wb['Раздел 1'])
    salary_fund_data = _load_salary_fund(wb['Раздел 2'])
    executive_salary = _load_executive_salaries(wb['Раздел 3'])
    salary_by_period_data = create_group_by_period_salary_data(salary_data)
    wb.close()
    logger.info('Generate xml file start')
    create_xml_file(
        temp_xml_file,
        xml_file,
        salary_by_period_data,
        salary_fund_data,
        executive_salary,
        guid,
        salary_data
    )
    delete_file(temp_xml_file)
    logger.info(f'Complete generate xml file: {file_name}')


if __name__ == '__main__':
    main(os.getcwd())
