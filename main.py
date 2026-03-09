from fastapi import FastAPI, Request # 👈 Request 추가
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates # 👈 Jinja2Templates 추가
import datetime

app = FastAPI()

# 🌟 templates 폴더를 연결합니다
templates = Jinja2Templates(directory="templates")

# 기존 read_root("/") 함수를 아래 코드로 덮어쓰세요
@app.get("/", response_class=HTMLResponse, tags=["웹페이지"])
async def read_root(request: Request):
    """Jinja2를 사용한 진짜 메인 홈페이지"""
    return templates.TemplateResponse("index.html", {"request": request})

# 화면이동 테스트를 위한 새로운 상태 페이지 엔드포인트 추가
@app.get("/status-page", response_class=HTMLResponse, tags=["웹페이지"])
async def show_status_page(request: Request):
    """Jinja2를 사용한 상태 확인 페이지"""
    return templates.TemplateResponse("status.html", {
        "request": request,
        "status": "정상 작동 중 (Running)",
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })