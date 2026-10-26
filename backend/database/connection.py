from idlelib import debugger

import pymysql
from pymysql  import Error
from datetime import datetime, timedelta
from backend.models.inspect_data import loadb005
#连接数据库
def get_connection(password):
    return pymysql.connect(
        host="localhost",
        user="root",
        port=3306,
        password=password,
        database="batterysoh",
        charset="utf8mb4",
        connect_timeout=5,
        autocommit=False
    )

#测试数据库是否连接成功
def test_connection(connection):
    with connection.cursor() as cursor:
        sql = "SELECT DATABASE();"
        cursor.execute(sql)
        database_name = cursor.fetchone()[0]
        print(f"成功连接到 MySQL {database_name}")

        cursor.execute("SHOW TABLES;")
        print("数据库中的表：")
        for row in cursor.fetchall():
            print("-", row[0])

#插入一条数据给batteries
def insert_data(connection,battery_id,reference_capacity_ah,source_file):
    with connection.cursor() as cursor:
        #检查是否已有已插入的数据
        cursor.execute(
            "SELECT battery_id FROM batteries WHERE battery_id = %s",
            (battery_id,)
        )
        if cursor.fetchone() is not None:
            print(f"{battery_id} 已存在，跳过插入")
            return
        #如果没有则插入
        sql = "INSERT INTO batteries VALUES (%s,%s,%s);"
        cursor.execute(sql,(battery_id,reference_capacity_ah,source_file))

#插入第一条数据
def insert_discharge_data(connection,battery_id,discharge_no, record):
    first_cycle = record["cycle"]
    measurements = first_cycle["data"]
    # 原始时间：[年, 月, 日, 时, 分, 秒]
    # 秒可能带小数，所以使用 timedelta 保留小数秒
    time_values = first_cycle["time"]
    temperature = float(first_cycle["ambient_temperature"])
    source_cycle_index = int(record["source_cycle_index"])
    capacity_ah = float(measurements.get("Capacity"))
    started_at = datetime(
        *[int(value) for value in time_values[:5]]
    ) + timedelta(seconds=float(time_values[5]))

    sql = """ INSERT INTO discharge_cycles (
    battery_id,
    discharge_no,
    ambient_temperature_c,
    source_cycle_index,
    started_at,
    capacity_ah
    ) 
    VALUES (%s,%s,%s,%s,%s,%s);"""

    with connection.cursor() as cursor:
        #判断插入的时候先查询，是否已经有这条数据了
        cursor.execute("""
        SELECT id
        FROM discharge_cycles
        WHERE battery_id = %s AND discharge_no = %s
        """,(battery_id,discharge_no))
        existing = cursor.fetchone()
        if existing is not None:
            print("这条循环已经插入")
            cycle_id = existing[0]
        else:
            cursor.execute(sql,(battery_id,discharge_no,temperature,source_cycle_index,started_at,capacity_ah))
            cycle_id = cursor.lastrowid
        return cycle_id

def insert_charge_sample(connection,cycle_id,record):
    measurements = record["cycle"]["data"]  # 第一条放电循环数据
    with connection.cursor() as cursor:
        #先查询是否已经有数据，有的话不插入，仅插入没插入的数据
        cursor.execute("""
        SELECT samples_no FROM discharge_samples
        WHERE cycle_id = %s
        """,(cycle_id,))
        existing_number = {
            row[0] for row in cursor.fetchall()
        }
        sql = """ INSERT INTO discharge_samples 
        (cycle_id,samples_no,elapsed_seconds,voltage_v,current_a,temperature_c,voltage_load,current_load)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """
        data = []
        for i in range(len(measurements["Time"])):
            sample_no = i + 1
            if sample_no in existing_number:
                continue
            data.append((
                cycle_id,
                 sample_no,
                 float(measurements["Time"][i]),
                 float(measurements["Voltage_measured"][i]),
                 float(measurements["Current_measured"][i]),
                 float(measurements["Temperature_measured"][i]),
                 float(measurements["Voltage_load"][i]),
                 float(measurements["Current_load"][i])
                 ))
        if len(data) == 0:
            print("采样点全部存在，不需要插入")
            return 0
        cursor.executemany(sql, data)
        return len(data)

#数据插入完成后检验是否数据库中存储的数据与原始文件的一致
def verify_discharge_data(connection,battery_id,discharge_data):
    expected_data = {discharge_no: len(record["cycle"]["data"]["Time"]) for discharge_no,record in enumerate(discharge_data,1)}
    qsql = """select c.discharge_no, count(s.samples_no) sample_num 
            from discharge_cycles as c 
            left join discharge_samples as s
            on c.id = s.cycle_id
            WHERE c.battery_id = %s
            GROUP BY c.id,c.discharge_no
            """
    with connection.cursor() as cursor:
        cursor.execute(qsql,(battery_id,))
        actual = dict(cursor.fetchall())

        if expected_data != actual:
            for discharge_no in (expected_data.keys() | actual.keys()):
                expect_count = expected_data.get(discharge_no)
                actual_count = actual.get(discharge_no)
                if expect_count != actual_count:
                    print(
                        f"第 {discharge_no} 次放电数量不一致："
                        f"原文件={expect_count}，数据库={actual_count}"
                    )
            raise ValueError("入库数量核对未通过")
        print("入库数量核对通过")
        print("放电循环数：", len(actual))
        print("采样点总数：", sum(actual.values()))

#按顺序执行
if __name__ == "__main__":
    discharge_data = loadb005()
    try:
        connection = get_connection("970616")
    except Error as e:  #判断数据库连接的异常
        print(f"数据库连接失败: {e}")
        raise
    else:
        try:
            test_connection(connection) #测试连接
            insert_data(connection,'B0005', 2.0, 'B0005.mat')   #插入B0005的基础信息
            total_inserted_samples = 0
            # 遍历所有放电记录，放电序号从1开始
            for discharge_num,record in enumerate(discharge_data,1):
                cycle_id = insert_discharge_data(
                    connection,
                    battery_id="B0005",
                    discharge_no=discharge_num,
                    record=record
                )
                sample_count = insert_charge_sample(connection,cycle_id, record)
                total_inserted_samples+=sample_count

                print(f"第{discharge_num}条放电循环插入成功")
                print(f"循环 ID {cycle_id} 处理完成，本次新增 {sample_count} 个采样点未提交")

                # 全部处理成功，再统一提交
                connection.commit()
                print(
                    f"提交成功！共处理 {len(discharge_data)} 次放电，"
                    f"本次新增 {total_inserted_samples} 个采样点"
                )
            verify_discharge_data(connection,"B0005",discharge_data)
        except Exception: #Python 绝大多数通用异常，适合在内层做数据库回滚等
            connection.rollback()
            raise

        finally:
            connection.close()

