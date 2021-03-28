import os
import uuid
from datetime import datetime

from openpyxl import load_workbook
from loguru import logger

from src.handlers import (
    load_salary,
    load_salary_fund,
    load_executive_salaries,
    create_group_by_period_salary_data,
    create_xml_file)
from src.settings import Settings

logger.add('report.log', enqueue=True)

settings = Settings()


def main(base_dir: str):
    """
    Read xlsx file from input folder and create xml report for the pension fund in folder output
    :param base_dir: str - current working directory
    :return: None
    """
    logger.info('Start load data')
    guid: str = str(uuid.uuid4())

    file_name = f'ПФР_{settings.code_to}_СИоЗП_{settings.reg_number}_{datetime.now().strftime("%Y%m%d")}_{guid}.xml'
    xml_file = os.path.join(base_dir, settings.output_dir, file_name)
    report_file = os.path.join(base_dir, settings.input_dir, settings.report)

    logger.info(f'Read file: {report_file}')

    wb = load_workbook(filename=report_file, read_only=True)
    salary_data = load_salary(wb['Раздел 1'])
    salary_fund_data = load_salary_fund(wb['Раздел 2'])
    executive_salary = load_executive_salaries(wb['Раздел 3'])
    salary_by_period_data = create_group_by_period_salary_data(salary_data)
    wb.close()

    logger.info('Generate xml file start')
    create_xml_file(
        xml_file,
        salary_by_period_data,
        salary_fund_data,
        executive_salary,
        guid,
        salary_data,
    )
    logger.info(f'Complete generate xml file: {file_name}')


if __name__ == '__main__':
    main(os.getcwd())
