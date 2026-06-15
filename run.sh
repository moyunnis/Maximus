#!/bin/bash
echo "  Запуск Maximus v1.0.0"

if [ ! -d "venv" ]; then
    echo "Виртуальное окружение venv не найдено."
    echo "Рань пж: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    read -p "Enter жмякни разок, прикол покажу..."
    exit 1
fi

source venv/bin/activate

python3 main.py

read -p "Нажмите Enter для выхода..."