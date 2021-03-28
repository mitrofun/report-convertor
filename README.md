# Конвертор для СИоЗП.2.57.3п

Генерирует xml для загрузки в пенсионный фонд из печатной формы xlsx файла СИоЗП.2.57.3п (Формы сбора информации о заработной плате работников государственных и муниципальных учреждений)

## Зависимости
- Python 3.8+
- openpyxl
- pydantic
- подробней в файле зависимостей requirements

## Разработка
Склонировать репозиторий
```
git clone https://github.com/mitrofun/report-convertor.git
```
Установить зависимости
```
cd report-convertor
pip install -r requirements/dev.txt
```
Создать настройки
```
cp example.ini settings.ini
```
Запуск конвертора
```
python converter.py
```

## Сборка исполнительного файла для Windows.
На Windows машине выполните
```
pip install https://github.com/pyinstaller/pyinstaller/tarball/develop
pyinstaller --clean --onefile --noconsole converter.py
```
Собранный exe файл находиться в папке dist проекта