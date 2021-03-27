import pytest

from converter import convert_experience, decompose_full_name


@pytest.mark.parametrize(
    'test_input, expected',
    [
        ('0 лет 00 мес', '00.00'),
        ('5 лет 10 мес', '05.10'),
        ('0 лет 06 мес', '00.06')
    ],
)
def test_convert_exchange(test_input, expected):
    assert convert_experience(test_input) == expected


@pytest.mark.parametrize(
    'test_input, expected',
    [
        ('Иванов Иван Иванович', ['Иванов', 'Иван', 'Иванович']),
        ('Иванов Иван Иванович оглы', ['Иванов', 'Иван', 'Иванович оглы']),
        ('Иванов Иван', ['Иванов', 'Иван', '']),
    ],
)
def test_decompose_full_name(test_input, expected):
    assert decompose_full_name(test_input) == expected
