from datetime import datetime
import pandas as pd
import os


def data_to_csv(filename, **columns):
    data = pd.DataFrame(columns)

    current_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")
    full_filename = f'../../data/raw/{filename}_{current_datetime}.csv'

    os.makedirs(os.path.dirname(full_filename), exist_ok=True)

    data.to_csv(full_filename, index=False, sep=',')
