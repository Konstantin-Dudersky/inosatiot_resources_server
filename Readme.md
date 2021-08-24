# Установка
1. Скачать проект с github
   
        $ mkdir ~/inosatiot && cd ~/inosatiot && sudo apt install git
        $ cd ~/inosatiot
        $ git clone https://github.com/Konstantin-Dudersky/inosatiot_resources_server.git
        $ cd inosatiot_resources_server

2. Создать файл с настройками config_inosatiot_resources_sim.yaml. Шаблон находится в setup/inosatiot_cfg.json_template.
       
        $ cp setup/config_example.yaml ../config_inosatiot_resources_server.yaml

   Прописать в файле настройки.


3. Установка библиотек python в файле setup/setup.sh
   
        $ chmod +x setup/setup.sh && setup/setup.sh

   Что делает скрипт:
   - Обновляет пакеты в системе
   - Устанавливает пакеты python
   - Создает виртуальное окружение venv, скачивает необходимые пакеты
   - Создает сервис systemd, устанавливает автозапуск
    
    
4. После установки можно запустить на выполнение через systemd
   
        $ sudo systemctl start config_inosatiot_resources_server.service  // запустить
        $ sudo systemctl stop config_inosatiot_resources_server.service  // остановить
        $ sudo systemctl restart config_inosatiot_resources_server.service  // перезапустить
        $ sudo systemctl status config_inosatiot_resources_server.service  // просмотреть статус

# Обновить проект
- Синхронизировать проект с github (локальные изменения теряются)
   
        $ cd ~/inosatiot/inosatiot_resources_server/
        $ chmod +x setup/update.sh && setup/update.sh

Файл настроек находится в вышестоящей папке, поэтому настройки остаются