import os
import pandas as pd
from datetime import datetime


def data_to_csv(filename, **columns):
    data = pd.DataFrame(columns)

    current_datetime = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    full_filename = f'../../data/raw/{filename}_{current_datetime}.csv'

    os.makedirs(os.path.dirname(full_filename), exist_ok=True)

    data.to_csv(full_filename, index=False, sep=',')
