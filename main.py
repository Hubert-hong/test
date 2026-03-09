from fastapi import FastAPI, HTTPException, Depends, status, File, UploadFile, Form, Header, Cookie
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
import json
from pathlib import Path

# FastAPI 앱 초기화
app = FastAPI(
    title="FastAPI 완전 가이드",
    description="FastAPI의 모든 주요 기능을 다루는 상세 예제",
    version="1.0.0"
)

# ==================== CORS 설정 ====================
# 다른 도메인에서의 요청 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 도메인 허용 (실무에서는 특정 도메인만)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== Pydantic 모델 정의 ====================

# 사용자 정보를 위한 기본 모델
class User(BaseModel):
    id: int
    name: str = Field(..., min_length=1, max_length=50, description="사용자 이름")
    email: str = Field(..., description="사용자 이메일")
    age: Optional[int] = Field(None, ge=0, le=150, description="사용자 나이")
    is_active: bool = True
    
    # 데이터 검증
    @validator('email')
    def email_must_be_valid(cls, v):
        if '@' not in v:
            raise ValueError('이메일이 유효하지 않습니다')
        return v

# 상품 정보 모델
class Item(BaseModel):
    id: int
    name: str
    price: float = Field(..., gt=0, description="가격은 0보다 커야 합니다")
    description: Optional[str] = None
    tax: Optional[float] = None
    tags: List[str] = []

# 상품 생성 요청에 사용할 모델 (id 없음)
class ItemCreate(BaseModel):
    name: str
    price: float = Field(..., gt=0)
    description: Optional[str] = None
    tax: Optional[float] = None
    tags: List[str] = []

# 포스트 모델
class Post(BaseModel):
    id: int
    title: str
    content: str
    author: str
    created_at: datetime = Field(default_factory=datetime.now)
    comments: List[str] = []

# 로그인 요청 모델
class LoginRequest(BaseModel):
    username: str
    password: str

# 로그인 응답 모델
class LoginResponse(BaseModel):
    token: str
    user: str
    message: str

# 상품 카테고리 Enum
class ItemCategory(str, Enum):
    ELECTRONICS = "전자제품"
    CLOTHING = "의류"
    FOOD = "음식"
    BOOKS = "책"

# ==================== 임시 데이터베이스 ====================
# 실무에서는 실제 데이터베이스 사용
users_db: Dict[int, User] = {
    1: User(id=1, name="김철수", email="kim@example.com", age=25),
    2: User(id=2, name="이영희", email="lee@example.com", age=30),
}

items_db: Dict[int, Item] = {
    1: Item(id=1, name="노트북", price=1500000, description="고성능 노트북", tags=["전자제품"]),
    2: Item(id=2, name="마우스", price=50000, description="무선 마우스", tags=["전자제품"]),
}

posts_db: Dict[int, Post] = {}

# ==================== 의존성 주입 ====================
# 쿼리 매개변수 검증
async def common_parameters(
    skip: int = 0, 
    limit: int = 10
):
    """일반적인 쿼리 매개변수"""
    return {"skip": skip, "limit": limit}

# API 키 검증 (간단한 예제)
async def verify_api_key(x_token: str = Header(...)):
    """API 키 검증"""
    if x_token != "secret-key":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API 키가 유효하지 않습니다"
        )
    return x_token

# 사용자 인증 (간단한 예제)
async def get_current_user(authorization: Optional[str] = Header(None)):
    """현재 로그인한 사용자 정보 가져오기"""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증이 필요합니다"
        )
    # 실무에서는 JWT 토큰 검증
    if authorization != "Bearer valid-token":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="토큰이 유효하지 않습니다"
        )
    return "current_user"

# ==================== 기본 GET 엔드포인트 ====================

@app.get("/", tags=["기본"])
async def read_root():
    """루트 엔드포인트"""
    return {
        "message": "FastAPI 완전 가이드에 오신 것을 환영합니다!",
        "version": "1.0.0"
    }

@app.get("/status", tags=["기본"])
async def get_status():
    """서버 상태 확인"""
    return {
        "status": "running",
        "timestamp": datetime.now(),
        "environment": "development"
    }

# ==================== 경로 매개변수 (Path Parameters) ====================

@app.get("/users/{user_id}", response_model=User, tags=["사용자"])
async def get_user(user_id: int = Field(..., gt=0, description="사용자 ID")):
    """
    특정 ID의 사용자 조회
    
    - **user_id**: 사용자의 고유 ID
    """
    if user_id not in users_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"사용자 {user_id}를 찾을 수 없습니다"
        )
    return users_db[user_id]

@app.get("/items/{item_id}", response_model=Item, tags=["상품"])
async def get_item(
    item_id: int = Field(..., gt=0),
    include_tax: bool = False
):
    """
    특정 ID의 상품 조회
    
    - **item_id**: 상품 ID
    - **include_tax**: 세금 포함 여부
    """
    if item_id not in items_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"상품 {item_id}를 찾을 수 없습니다"
        )
    return items_db[item_id]

# 경로 매개변수에 Enum 사용
@app.get("/items/category/{category}", tags=["상품"])
async def get_items_by_category(category: ItemCategory):
    """
    카테고리별 상품 조회
    
    - **category**: 상품 카테고리 (ELECTRONICS, CLOTHING, FOOD, BOOKS)
    """
    return {
        "category": category,
        "message": f"{category.value} 카테고리의 상품들입니다"
    }

# ==================== 쿼리 매개변수 (Query Parameters) ====================

@app.get("/users/", tags=["사용자"], response_model=List[User])
async def list_users(
    skip: int = 0,
    limit: int = 10,
    is_active: Optional[bool] = None
):
    """
    사용자 목록 조회
    
    - **skip**: 건너뛸 사용자 수 (기본값: 0)
    - **limit**: 반환할 최대 사용자 수 (기본값: 10)
    - **is_active**: 활성 상태 필터 (선택사항)
    """
    users = list(users_db.values())
    if is_active is not None:
        users = [u for u in users if u.is_active == is_active]
    return users[skip : skip + limit]

@app.get("/search/", tags=["검색"])
async def search(
    q: str = '',
    skip: int = 0,
    limit: int = 10,
    sort_by: str = "name"
):
    """
    검색 엔드포인트
    
    - **q**: 검색 쿼리
    - **skip**: 건너뛸 결과 수
    - **limit**: 반환할 최대 결과 수
    - **sort_by**: 정렬 기준
    """
    return {
        "query": q,
        "skip": skip,
        "limit": limit,
        "sort_by": sort_by,
        "results": [],
        "total_results": 0
    }

# ==================== POST 엔드포인트 (요청 본문) ====================

@app.post("/users/", response_model=User, status_code=status.HTTP_201_CREATED, tags=["사용자"])
async def create_user(user: User):
    """
    새로운 사용자 생성
    
    요청 본문:
    - **id**: 사용자 ID
    - **name**: 사용자 이름
    - **email**: 사용자 이메일
    - **age**: 사용자 나이 (선택사항)
    - **is_active**: 활성 상태 (기본값: True)
    """
    if user.id in users_db:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="사용자 ID가 이미 존재합니다"
        )
    users_db[user.id] = user
    return user

@app.post("/items/", response_model=Item, status_code=status.HTTP_201_CREATED, tags=["상품"])
async def create_item(item: ItemCreate):
    """
    새로운 상품 생성
    """
    new_id = max([0] + list(items_db.keys())) + 1
    new_item = Item(id=new_id, **item.dict())
    items_db[new_id] = new_item
    return new_item

@app.post("/posts/", response_model=Post, status_code=status.HTTP_201_CREATED, tags=["게시물"])
async def create_post(post: Post, current_user = Depends(get_current_user)):
    """
    새로운 게시물 생성 (인증 필요)
    """
    posts_db[post.id] = post
    return post

# ==================== PUT/PATCH 엔드포인트 (수정) ====================

@app.put("/users/{user_id}", response_model=User, tags=["사용자"])
async def update_user(
    user_id: int,
    updated_user: User
):
    """
    기존 사용자 정보 완전히 수정 (PUT)
    """
    if user_id not in users_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"사용자 {user_id}를 찾을 수 없습니다"
        )
    users_db[user_id] = updated_user
    return updated_user

@app.patch("/items/{item_id}", tags=["상품"])
async def partial_update_item(
    item_id: int,
    item_update: dict
):
    """
    기존 상품 정보 부분 수정 (PATCH)
    """
    if item_id not in items_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"상품 {item_id}를 찾을 수 없습니다"
        )
    item = items_db[item_id]
    item_data = item.dict()
    item_data.update(item_update)
    updated_item = Item(**item_data)
    items_db[item_id] = updated_item
    return updated_item

# ==================== DELETE 엔드포인트 ====================

@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["사용자"])
async def delete_user(user_id: int):
    """
    사용자 삭제
    """
    if user_id not in users_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"사용자 {user_id}를 찾을 수 없습니다"
        )
    del users_db[user_id]

@app.delete("/items/{item_id}", tags=["상품"])
async def delete_item(item_id: int):
    """
    상품 삭제
    """
    if item_id not in items_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"상품 {item_id}를 찾을 수 없습니다"
        )
    del items_db[item_id]
    return {"message": f"상품 {item_id}가 삭제되었습니다"}

# ==================== 양식 데이터 (Form Data) ====================

@app.post("/login/", response_model=LoginResponse, tags=["인증"])
async def login(
    username: str = Form(...),
    password: str = Form(...)
):
    """
    로그인 (form-data 사용)
    """
    if username == "admin" and password == "password":
        return LoginResponse(
            token="token-123456",
            user=username,
            message="로그인 성공!"
        )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="사용자명 또는 비밀번호가 잘못되었습니다"
    )

# ==================== 파일 업로드 ====================

@app.post("/upload/", tags=["파일"])
async def upload_file(file: UploadFile = File(...)):
    """
    단일 파일 업로드
    """
    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "size": len(await file.read()),
        "message": "파일 업로드 성공!"
    }

@app.post("/upload-multiple/", tags=["파일"])
async def upload_multiple_files(files: List[UploadFile] = File(...)):
    """
    여러 파일 업로드
    """
    file_info = []
    for file in files:
        content = await file.read()
        file_info.append({
            "filename": file.filename,
            "content_type": file.content_type,
            "size": len(content)
        })
    return {"uploaded_files": file_info}

# ==================== 복합 요청 (본문 + 양식 + 파일) ====================

@app.post("/upload-with-data/", tags=["파일"])
async def upload_with_data(
    description: str = Form(...),
    priority: int = Form(...),
    file: UploadFile = File(...)
):
    """
    파일과 추가 데이터를 함께 업로드
    """
    content = await file.read()
    return {
        "description": description,
        "priority": priority,
        "filename": file.filename,
        "file_size": len(content)
    }

# ==================== 헤더 및 쿠키 ====================

@app.get("/headers-example/", tags=["헤더"])
async def read_header_example(
    x_custom_header: Optional[str] = Header(None),
    user_agent: Optional[str] = Header(None)
):
    """
    요청 헤더 읽기
    """
    return {
        "x_custom_header": x_custom_header,
        "user_agent": user_agent
    }

@app.get("/protected/", tags=["보안"])
async def protected_route(x_token: str = Header(...)):
    """
    헤더 기반 토큰 검증이 필요한 엔드포인트
    """
    if x_token != "super-secret-token":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="토큰이 유효하지 않습니다"
        )
    return {"message": "접근 허가됨!"}

# ==================== 다양한 응답 형식 ====================

@app.get("/response-example/", tags=["응답"])
async def response_example(detailed: bool = False):
    """
    쿼리 매개변수에 따라 다른 응답 반환
    """
    if detailed:
        return {
            "data": {
                "name": "김철수",
                "email": "kim@example.com",
                "created_at": datetime.now()
            },
            "metadata": {
                "version": "1.0.0",
                "timestamp": datetime.now()
            }
        }
    return {"name": "김철수", "email": "kim@example.com"}

@app.get("/list-with-pagination/", tags=["응답"])
async def list_with_pagination(
    page: int = 1,
    page_size: int = 10,
    commons: dict = Depends(common_parameters)
):
    """
    페이지네이션 기능이 있는 목록 조회
    """
    return {
        "page": page,
        "page_size": page_size,
        "total_items": 100,
        "total_pages": 10,
        "items": [],
        "commons": commons
    }

# ==================== 에러 처리 ====================

@app.get("/division/{dividend}/{divisor}", tags=["계산"])
async def divide(
    dividend: float,
    divisor: float
):
    """
    두 수를 나누는 계산 (에러 처리 예제)
    """
    if divisor == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="0으로 나눌 수 없습니다"
        )
    return {
        "result": dividend / divisor,
        "dividend": dividend,
        "divisor": divisor
    }

@app.get("/validate/{value}", tags=["검증"])
async def validate_value(value: int = Field(..., ge=1, le=100)):
    """
    값이 1-100 범위인지 검증
    """
    return {
        "value": value,
        "is_valid": True,
        "message": f"{value}는 유효한 값입니다"
    }

# ==================== 커스텀 에러 핸들링 ====================

class CustomException(Exception):
    def __init__(self, message: str):
        self.message = message

@app.exception_handler(CustomException)
async def custom_exception_handler(request, exc):
    return {
        "error": exc.message,
        "status_code": 400
    }

@app.get("/custom-error/", tags=["에러"])
async def trigger_custom_error(trigger: bool = False):
    """
    커스텀 에러 발생 테스트
    """
    if trigger:
        raise CustomException("이것은 커스텀 에러입니다")
    return {"message": "정상적으로 실행됨"}

# ==================== 고급 기능 ====================

@app.get("/data-example/", tags=["데이터"])
async def data_example():
    """
    여러 타입의 데이터 반환 예제
    """
    return {
        "string": "문자열",
        "integer": 42,
        "float": 3.14,
        "boolean": True,
        "list": [1, 2, 3, 4, 5],
        "dict": {"key": "value", "nested": {"deep": "data"}},
        "null": None,
        "datetime": datetime.now(),
        "date_with_time": datetime.now().isoformat()
    }

@app.post("/calculate/", tags=["계산"])
async def calculate(
    operation: str,
    a: float,
    b: float
):
    """
    간단한 계산 기능
    
    - **operation**: 연산자 (+, -, *, /)
    - **a**: 첫 번째 수
    - **b**: 두 번째 수
    """
    if operation == "+":
        result = a + b
    elif operation == "-":
        result = a - b
    elif operation == "*":
        result = a * b
    elif operation == "/":
        if b == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="0으로 나눌 수 없습니다"
            )
        result = a / b
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="지원하지 않는 연산입니다"
        )
    
    return {
        "operation": operation,
        "a": a,
        "b": b,
        "result": result
    }

# ==================== 웰컴 엔드포인트 (한국어 예제) ====================

@app.get("/welcome/{name}", tags=["한국어 예제"])
async def welcome(
    name: str,
    age: Optional[int] = None
):
    """
    사용자를 환영하는 엔드포인트
    """
    message = f"{name}님, 환영합니다!"
    if age:
        message += f" {age}살이시네요!"
    return {
        "message": message,
        "timestamp": datetime.now()
    }
