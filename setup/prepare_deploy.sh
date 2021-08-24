# запустить скрипт перед публикацией на github

echo
echo "-----> Create requirements.txt:"
pip freeze >setup/requirements.txt

echo
echo "-----> Replace Debug = True"
python3 setup/lib/replace_debug_true.py
