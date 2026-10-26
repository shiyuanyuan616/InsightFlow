import os
from http import HTTPStatus
# from http.client import HTTPException
import uvicorn
from fastapi import FastAPI,HTTPException
from pymysql import Error
from backend.database.connection import get_connection

#创建fastapi实例
app = FastAPI(title="InsightFlow 电池分析平台") #这里是创建一个 FastAPI 应用对象，并保存到变量 app
#title 是应用标题，主要显示在接口文档中

#定义根路径的 GET 路由
@app.get("/")
async def home():
    return {"message": "后端启动成功"}

@app.get("/api/health")
async def health():
    return {"status": "ok"}

@app.get("/api/batteries_deg/{battery_id}")
def batteries_deg(battery_id: str):
    connection = None
    try:
        connection = get_connection("970616")
        with connection.cursor() as cursor:
            sql="""select discharge_no,ambient_temperature_c,capacity_ah from discharge_cycles where battery_id=%s"""
            cursor.execute(sql,(battery_id,))
            results = cursor.fetchall()
    except Error as e:
        print(f"数据库查询失败：{e}")
        raise HTTPException(status_code=503,detail="数据库暂时不可用")
    else:
        if not results:
            raise HTTPException(
                status_code=404,
                detail="没有找到该电池的放电数据"
            )
        return {
            "status_code": 200,
            "battery_id": battery_id,
            "results": results
        }
    finally:
        if connection is not None:
            connection.close()

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000
    )