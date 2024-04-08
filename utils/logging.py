import json
import os
from datetime import datetime
import uuid

def save_log(log_data):
    date_str = datetime.now().strftime('%Y-%m-%d')
    time_str = datetime.now().strftime('%H-%M-%S')
    dir_path = f'data/logging/{date_str}/{time_str}'

    os.makedirs(dir_path, exist_ok=True)

    file_name = f'{uuid.uuid4()}.json'

    file_path = os.path.join(dir_path, file_name)

    with open(file_path, 'w') as file:
        json.dump(log_data, file)

    print(f'Log saved to {file_path}')