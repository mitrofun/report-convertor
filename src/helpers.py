from typing import List

from dateparser import DateDataParser


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


def decompose_full_name(full_name: str) -> List[str]:
    result = full_name.split(' ')
    if len(result) == 4:
        return [result[0], result[1], f'{result[2]} {result[3]}']
    if len(result) == 2:
        result.append('')
        return result
    return result
