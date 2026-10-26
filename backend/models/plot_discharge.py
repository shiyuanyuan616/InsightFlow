import matplotlib.pyplot as plt
from pymysql import Error
import pandas as pd
import numpy as np
from backend.database.connection import get_connection
import sys

print(sys.executable)
print(sys.version)

##拿到B0005的循环点位数据，先绘制容量和循环趋势的衰减图表，数据表discharge_cycle
def get_discharge_data(connection):
    with connection.cursor() as cursor:
        sql = "select discharge_no,ambient_temperature_c,capacity_ah from discharge_cycles"
        cursor.execute(sql)
        cycles = list(cursor.fetchall())
        print(cycles)
        x,t,y = zip(*cycles)
        temperature_c = t[0]
        fig,ax = plt.subplots(figsize=(10,10))
        ax.plot(x,y,label=f'B0005 ({temperature_c}℃)')
        ax.set(xlabel='Discharge_No',ylabel='Capacity(Ah)')
        ax.set_title(f'Degradation curve')
        ax.grid()
        ax.legend()
        plt.show()
        plt.tight_layout()

if __name__ == "__main__":
    try:
       connection = get_connection("970616")
    except Error as e:
        print(f"数据库连接失败: {e}")
        raise
    else:
        print("successful！")
        try:
            get_discharge_data(connection)
        finally:
            connection.close()