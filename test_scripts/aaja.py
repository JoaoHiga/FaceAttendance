import os.path
from collections import Counter
import numpy as np
from deepface import DeepFace
import pandas as pd
import pprint

DeepFace.find('FIRMA ALAN.png', db_path='../faces_databases', enforce_detection=True)

try:
    DeepFace.find('FIRMA ALAN.png', db_path='../faces_databases', enforce_detection=True)
    df = pd.DataFrame(DeepFace.find('FIRMA ALAN.png', db_path='../faces_databases', enforce_detection=True)[:][:][0])
    names = []
    for n in df[df.columns[0]]:
        names.append(os.path.split(os.path.split(n)[0])[1])
        # print(n)
        # print(os.path.split(os.path.split(n)[0])[1])
    print(Counter(names).most_common(n=1)[0][0])
except ValueError:
    pass


