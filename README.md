# pyhub-htmx-examples

이 프로젝트는 Melon 차트 데이터를 가져와 Django 데이터베이스에 저장하는 기능을 제공합니다.

## 초기 설정 및 실행 방법

1. 가상환경 생성 및 활성화:

```bash
python -m venv venv

venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux
```

2. 필요한 패키지 설치:

```bash
pip install -r requirements.txt
```

3. 데이터베이스 마이그레이션:

```bash
python manage.py migrate
```

4. Melon 차트 데이터 가져오기:

```bash
python manage.py import_melon_chart melon/assets/20240907.json
```

이 명령은 `melon/assets/20240907.json` 파일에서 Melon 차트 데이터를 읽어와 데이터베이스에 저장합니다.

5. 개발 서버 실행:

```bash
python manage.py runserver
```

이제 `http://localhost:8000`에서 프로젝트에 접근할 수 있습니다.

## 주의사항

- `import_melon_chart` 명령은 JSON 파일의 경로를 인자로 받습니다. 필요에 따라 파일 경로를 변경하세요.
- 데이터 가져오기 전에 반드시 데이터베이스 마이그레이션을 실행해야 합니다.
