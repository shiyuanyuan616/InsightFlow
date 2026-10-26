from fastapi import FastAPI
#创建fastapi实例
app = FastAPI(title="InsightFlow 电池分析平台")


#定义根路径的 GET 路由
@app.get("/")
async def root():
    return {"message": "Hello World"}