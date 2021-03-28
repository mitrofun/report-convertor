from typing import Tuple

from decouple import config
from pydantic import BaseSettings


ALLOW_CATEGORY_CODE = (201, 221, 291, 211, 232, 233, 242, 243, 261, 401, 431, 411, 421, 501, 311, 281, 100, 600)
REPORT = config('REPORT', default='example.xlsx')
INPUT_DIR = config('INPUT_DIR', default='input')
OUTPUT_DIR = config('OUTPUT_DIR', default='output')
CODE_TO = config('CODE_TO', default='201000')
REG_NUMBER = config('REG_NUMBER', default='034012008689')


class Settings(BaseSettings):
    allow_category_code: Tuple = ALLOW_CATEGORY_CODE
    report: str = REPORT
    input_dir: str = INPUT_DIR
    output_dir: str = OUTPUT_DIR
    code_to: str = CODE_TO
    reg_number: str = REG_NUMBER
