"""
04_async — 异步处理
====================

学习要点:
- async def 路由 vs def 路由:什么时候该用 async
- await 调用下游异步 IO(httpx、asyncio.sleep)
- BackgroundTasks:返回响应后再执行「不阻塞客户端」的耗时操作
- asyncio.gather:并发多个 IO,对比串行的耗时

运行方式:
    cd fastapi/04_async
    uvicorn main:app --reload
"""

import asyncio

import httpx
from fastapi import BackgroundTasks, FastAPI


app = FastAPI(title="04_async 示例", version="0.1.0")


# ---------------------------------------------------------------------------
# 1. async def vs def
# ---------------------------------------------------------------------------
# async def 定义的路由里,可以用 await 调用其他异步函数。
# 如果路由里只是纯计算、没有 IO,用普通 def 反而更好(不会多一层协程开销)。
@app.get("/")
async def root():
    return {"message": "hello from async route"}


# ---------------------------------------------------------------------------
# 2. await 一个异步 IO(用 asyncio.sleep 模拟)
# ---------------------------------------------------------------------------
# 真实项目里,await 的对象通常是:
#   - httpx.AsyncClient(异步 HTTP 调用)
#   - 异步数据库驱动(SQLAlchemy async、databases、Tortoise 等)
#   - redis.asyncio / aiofiles 等
# 这里用 asyncio.sleep 模拟一个「耗时 1 秒」的操作。
@app.get("/slow")
async def slow():
    await asyncio.sleep(1)  # 这 1 秒里事件循环可以处理其他请求,不会卡住整个进程
    return {"waited": "1s"}


# ---------------------------------------------------------------------------
# 3. 串行 vs 并发:asyncio.gather 的差别
# ---------------------------------------------------------------------------
# 串行:一个一个 await,总耗时 = 各个任务耗时之和。
@app.get("/serial")
async def serial():
    results = []
    for i in range(3):
        # 每次等 1 秒,3 次一共 3 秒。
        await asyncio.sleep(1)
        results.append(f"task-{i} done")
    return {"results": results, "mode": "serial", "cost_seconds": 3}


# 并发:用 asyncio.gather 把多个协程一起调度,总耗时 ≈ 最慢的那个。
@app.get("/concurrent")
async def concurrent():
    async def task(i: int) -> str:
        await asyncio.sleep(1)
        return f"task-{i} done"

    # gather 会并发调度 3 个 task,3 个都在等 sleep(1),
    # 实际墙钟时间只有约 1 秒(而不是 3 秒)。
    results = await asyncio.gather(*[task(i) for i in range(3)])
    return {"results": results, "mode": "concurrent", "cost_seconds": 1}


# ---------------------------------------------------------------------------
# 4. 真实的异步 HTTP 调用:httpx.AsyncClient
# ---------------------------------------------------------------------------
# httpx.AsyncClient 是异步版的 requests,适合在 async 路由里调用下游 API。
# 注意:AsyncClient 应该被复用(每次 new 一个会浪费连接池),这里为了示例简单。
@app.get("/fetch")
async def fetch():
    async with httpx.AsyncClient(timeout=10) as client:
        # 调用一个公开的测试 API,await 期间事件循环可以处理其他请求。
        resp = await client.get("https://httpbin.org/get")
        return {"status": resp.status_code, "json": resp.json()}


# ---------------------------------------------------------------------------
# 5. BackgroundTasks:响应后做的事
# ---------------------------------------------------------------------------
# 有些事(写日志、发通知、刷新缓存)客户端不需要等,
# 可以丢到 BackgroundTasks 里,响应先返回,任务在响应后跑。
def _write_log(msg: str):
    # 这个函数会被放在后台执行,客户端已经拿到响应了。
    # 这里用 print 模拟写日志,实际项目里可能是写文件 / 发 Kafka。
    print(f"  [background] {msg}")


@app.post("/notify")
async def notify(msg: str, background_tasks: BackgroundTasks):
    # 把任务丢进 background_tasks,但不阻塞当前响应。
    background_tasks.add_task(_write_log, msg)
    # 客户端立刻收到响应,写日志在后台悄悄进行。
    return {"message": "accepted, will process in background"}
