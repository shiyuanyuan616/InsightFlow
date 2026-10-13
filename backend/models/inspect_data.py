from builtins import print

import numpy as np
import pandas as pd
import  matplotlib.pyplot as plt
from sklearn import linear_model
from pathlib import Path
from scipy.io import loadmat

#全局变量
fname = ""

#加载数据
def loadfile(filename):
    return loadmat(filename, simplify_cells=True)
    print(data.keys())

#当只运行该文档，才会进行文件读取
if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent.parent
    discharge_data = []
    def loadb005(): #加载B005数据
        global fname
        fname = root / "datasets"/"raw"/"B0005.mat"
        file_data = loadfile(fname) #加载数据 字典结构 dict_keys(['__header__', '__version__', '__globals__', 'B0005'])

        print(file_data.keys())
        battery = file_data['B0005']
        print(battery.keys())
        cycles = battery['cycle']
        # first_data = cycles[0]['data']
        # print(first_data)

        #筛选放电记录，并检查第一条放电的数据结构
        for source_index,cycle in enumerate(cycles,1):
            if cycle["type"] == "discharge":
                discharge_data.append({
                    "source_cycle_index":source_index, #原始数据里的第几次循环
                    "cycle":cycle           #循环数据
                })
        print("全部的数据有",len(cycles))
        print("放电数据有",len(discharge_data))

        #判断是否有保存放电数据
        if not discharge_data:
            raise ValueError("没有找到放电记录")

        # 查看第一条放电详细数据
        first_discharge  = discharge_data[0]
        cycle_data = first_discharge["cycle"] #第一条放电全数据
        measurements = cycle_data['data']       #测量点数据
        print(cycle_data)
        print("\n第一条放电：")
        print("原始操作序号：", first_discharge["source_cycle_index"])
        print("开始时间：", cycle_data["time"])
        print("环境温度：", cycle_data["ambient_temperature"])
        print("测量字段：", measurements.keys())
        print("放电容量（Ah）：", measurements.get("Capacity"))

        #检查时间、电压、电流、和温度数据
        #检查每个特征是否都有同样个数的值
        mea_fileds = ['Voltage_measured', 'Current_measured', 'Temperature_measured', 'Current_load', 'Voltage_load',
                      'Time']
        total_samples = 0
        for discharge_no, record in enumerate(discharge_data, 1):
            sample_data = record["cycle"]["data"]
            sample_lengths = [len(sample_data[field]) for field in mea_fileds]  #5个字段的采样点个数应该一致
            print(f"第{discharge_no}个放电循环的6组采样点个数为{sample_lengths}")
            #判断如果每个放电循环去重后，如果不是只留1个数据，或者这组是空数据，那么则抛出异常；
            if len(set(sample_lengths)) != 1 or sample_lengths[0] == 0:
                raise ValueError(
                    f"第 {discharge_no} 次放电数组长度异常："
                    f"{dict(zip(mea_fileds, sample_lengths))}"
                )
            #检查数值是否有效、时间是否递增
            for field in mea_fileds:
                values = np.asarray(sample_data[field], dtype=float)
                #检查六个数组中是否有 NaN 或无穷大
                if not np.isfinite(values).all():
                #np.isfinite(values)逐个判断 `values` 里**每一个元素是不是有限正常数值，输出布尔数组；布尔数组调用；`np.nan`（缺失值）、`np.inf`（正无穷）、`-np.inf`（负无穷） `.all()`：**全部元素都为 True 才返回 True；只要有一个 False，就返回 False**
                    raise ValueError(
                        f"第 {discharge_no} 次放电的 {field} 存在缺失或无穷大"
                    )
            #判断时间是否递增
            times = np.asarray(sample_data["Time"], dtype=float)
            if np.any(times < 0) or np.any(np.diff(times)<=0):
                #any对布尔数组：只要有至少一个 True → 返回 True；全部 False 才返回 False
                raise ValueError(
                    f"第 {discharge_no} 次放电的时间存在负值、重复或倒序"
                )
            #检查容量是否是正值或者不小于0
            #asarray读取容量，转为一维float数组,没有就是空数组.reshape(-1)压扁为以为数组
            capacity = np.asarray(sample_data.get("Capacity",[]), dtype=float).reshape(-1)
            #.size获取数组元素个数不等于1，或者不是有限正数，或者其中的任何一个<0，不能为负数
            if (
                capacity.size != 1
                or not np.isfinite(capacity).all()
                or np.any(capacity < 0)
            ):
                raise ValueError(
                   f"第 {discharge_no} 次放电的容量无效：{capacity}"
                )
            total_samples += sample_lengths[0]
        print("全部放电记录检查通过")
        print("放电次数：", len(discharge_data))
        print("采样点总数：", total_samples)
    #调用加载B005的函数
    loadb005()
