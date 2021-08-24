out = []

with open("inosatiot_resources_server/settings.py") as f:
    for line in f.readlines():
        # print(line.replace(" ", "").lower())
        if line.replace(" ", "").lower().strip() == 'debug=true':
            print('Replace DEBUG = True to DEBUG = False')
            out.append('DEBUG = False\n')
        else:
            out.append(line)

with open("inosatiot_resources_server/settings.py", "w") as f:
    f.writelines(out)
