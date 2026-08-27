<p align="center">
  <img src="assets/banner.png" alt="SearchForge Banner" width="100%"/>
</p>

# SearchForge

Google Drive üzerindeki PDF ve dokümanları web üzerinden arayan ve okuyan sistem.

## Mimari Özet

```
Frontend (Next.js) → Backend (FastAPI) → Google Drive API
```

- Dosyalar Google Drive'da kalır, sunucuda kalıcı kopya tutulmaz
- Backend Service Account ile Drive'a erişir, credentials frontend'e sızmaz
- PDF.js ile tarayıcıda yerleşik okuma
- Anahtar kelime + dosya adı araması, snippet ve sayfa numarası ile

---

## Gereksinimler

- Python 3.10+
- Node.js 18+
- Google Cloud projesi ve Service Account
- Google Drive klasörü (Service Account'a Viewer yetkisi verilmiş)

---

## 1. Google Drive API Kurulumu

### a. Google Cloud Console

1. [console.cloud.google.com](https://console.cloud.google.com) adresine gidin
2. Yeni proje oluşturun veya mevcut projeyi seçin
3. **APIs & Services → Enable APIs** bölümünden **Google Drive API**'yi etkinleştirin

### b. Service Account Oluşturma

1. **IAM & Admin → Service Accounts → Create Service Account**
2. İsim verin (örn: `searchforge-reader`)
3. **Create and Continue**
4. Role eklemek zorunlu değil (Drive paylaşımı yeterli)
5. **Done**
6. Oluşturulan Service Account'a tıklayın → **Keys → Add Key → Create New Key → JSON**
7. JSON dosyasını indirin

### c. Drive Klasörünü Paylaşma

1. Google Drive'da kaynak klasörünüze sağ tıklayın → **Paylaş**
2. Service Account e-posta adresini ekleyin (örn: `searchforge-reader@project-id.iam.gserviceaccount.com`)
3. Yetki: **Görüntüleyici (Viewer)**
4. Klasör ID'sini alın: Drive'daki klasörü açın, URL'deki son kısım folder ID'dir
   ```
   https://drive.google.com/drive/folders/BURASI_FOLDER_ID
   ```

---

## 2. Backend Kurulumu

```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### Environment Variables

```bash
cp .env.example .env
```

`.env` dosyasını düzenleyin:

```env
GOOGLE_DRIVE_FOLDER_ID=your_folder_id_here
GOOGLE_SERVICE_ACCOUNT_FILE=/güvenli/yol/service-account.json
FRONTEND_URL=http://localhost:3000
SEARCH_RESULT_LIMIT=20
MAX_SNIPPETS_PER_FILE=3
CACHE_TTL_SECONDS=300
CACHE_MAX_SIZE=100
SNIPPET_CONTEXT_CHARS=150
```

> **Önemli:** Service Account JSON dosyasını proje dizinine koymayın.
> Güvenli bir konuma yerleştirin ve tam yolu `GOOGLE_SERVICE_ACCOUNT_FILE`'a yazın.

### Backend'i Başlatma

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

API: http://localhost:8000/api/docs

---

## 3. Frontend Kurulumu

```bash
cd frontend
npm install
```

### Environment Variables

```bash
cp .env.local.example .env.local
```

`.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Frontend'i Başlatma

```bash
cd frontend
npm run dev
```

Uygulama: http://localhost:3000

---

## 4. API Endpointleri

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| GET | `/api/health` | Sistem ve Drive bağlantı durumu |
| GET | `/api/search?q=...&type=pdf&folder=...` | Doküman arama |
| GET | `/api/documents/{file_id}` | Doküman metadata |
| GET | `/api/documents/{file_id}/content` | PDF stream (inline) |
| GET | `/api/folders` | Klasör listesi |

### Arama Parametreleri

- `q` — Arama sorgusu (zorunlu)
- `type` — `all`, `pdf`, `docx`, `other` (opsiyonel, varsayılan: `all`)
- `folder` — Klasör yolu filtresi (opsiyonel)

---

## 5. Proje Yapısı

```
searchforge/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI uygulama giriş noktası
│   │   ├── api/
│   │   │   ├── search.py        # /api/search endpoint
│   │   │   └── documents.py     # /api/documents endpoints
│   │   ├── services/
│   │   │   ├── drive_service.py # Google Drive API entegrasyonu
│   │   │   ├── search_service.py# Arama mantığı
│   │   │   ├── pdf_service.py   # PyMuPDF ile text extraction
│   │   │   └── cache_service.py # TTL cache
│   │   ├── models/
│   │   │   └── search.py        # Pydantic modelleri
│   │   ├── core/
│   │   │   ├── config.py        # Environment settings
│   │   │   └── security.py      # Validation & sanitization
│   │   └── utils/
│   ├── requirements.txt
│   ├── .env.example
│   └── .gitignore
│
└── frontend/
    ├── app/
    │   ├── page.tsx             # Ana arama sayfası
    │   └── document/[id]/
    │       └── page.tsx         # PDF reader sayfası
    ├── components/
    │   ├── SearchBar.tsx
    │   ├── SearchResult.tsx
    │   ├── SearchFilters.tsx
    │   └── PdfViewer.tsx
    ├── lib/
    │   └── api.ts               # API istemci fonksiyonları
    └── types/
        └── index.ts             # TypeScript tipleri
```

---

## 6. Güvenlik Notları

- Service Account JSON'u asla git'e commit etmeyin
- `.env` dosyasını asla commit etmeyin
- `GOOGLE_SERVICE_ACCOUNT_FILE` sunucu dışındaki bir yolu işaret etmeli
- Tüm `file_id` istekleri, izin verilen Drive klasörü altında olup olmadığı doğrulanır
- CORS sadece `FRONTEND_URL`'e izin verir (production'da wildcard kullanmayın)
- Rate limiting için altyapı hazır; production'da nginx veya fastapi-limiter eklenebilir

---

## 7. Production Deployment Notları

### Backend (örn. VPS / shared hosting)

```bash
pip install gunicorn
gunicorn app.main:app -w 2 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

- `FRONTEND_URL`'i production domain'inize güncelleyin
- Reverse proxy olarak nginx kullanın
- Service Account dosyasını `/etc/searchforge/service-account.json` gibi güvenli bir yola koyun

### Frontend (örn. Vercel / Netlify)

```bash
npm run build
```

- `NEXT_PUBLIC_API_URL` environment variable'ını backend adresinize ayarlayın

---

## 8. İleride Eklenebilecek Özellikler

Mevcut servis katmanları aşağıdakileri eklemek için uygundur:

- **Semantic Search** — Embedding + pgvector ile hybrid search
- **OCR** — Taranmış PDF'ler için Tesseract/Surya entegrasyonu
- **Kullanıcı hesapları** — Auth katmanı eklenebilir
- **Arama geçmişi** — Veritabanı katmanı eklenebilir
- **Admin panel** — Klasör ve dosya yönetimi

---

## Hızlı Başlangıç (Özet)

```bash
# Terminal 1 — Backend
cd backend && python -m venv venv && venv/Scripts/activate
pip install -r requirements.txt
# .env dosyasını düzenle
uvicorn app.main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend && npm install
# .env.local dosyasını düzenle
npm run dev
```

http://localhost:3000 adresini açın ve aramaya başlayın.