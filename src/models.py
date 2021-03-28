from enum import Enum
from typing import List, Optional

from loguru import logger
from pydantic import (
    BaseModel,
    Field,
    validator,
    root_validator,
)

from src.helpers import convert_experience, decompose_full_name, get_mount_number
from src.settings import Settings

settings = Settings()


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
        if v not in settings.allow_category_code:
            logger.error(f'Error in staff category code: {v}.Allow values only {settings.allow_category_code}.')
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
        fields = ('last_name', 'first_name', 'middle_name')
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
