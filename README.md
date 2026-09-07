# S&P 500 Analysis

S&P 500 şirketlerini temel değerleme, analist hedefleri ve makine öğrenmesi sinyalleriyle karşılaştıran karar paneli.

## Klasörler

- `frontend/`: React/JSX dashboard.
- `backend/`: FastAPI ve veri güncelleme kodu.
- `backend/models/`: Colab'dan alınan eğitilmiş modeller.
- `data/`: Güncel sonuç, tahmin kayıtları ve tarihli snapshot'lar.
- `.github/workflows/`: Manuel/zamanlanmış veri güncellemesi ve dashboard kontrolü.

## Mevcut durum — Rev 2.1

- 503 şirketlik Rev 2 snapshot dahildir.
- Temel ve analist hedefleri net fiyat olarak gösterilebilir.
- `notebooks/amerikan_borsa_sp500_rev2.ipynb` doğrudan 12 aylık getiri ve hedef fiyat üretmek üzere hazırlanmıştır.
- Notebook ilk kez çalıştırılınca Rev 2 model paketi oluşturulur; paketteki `regression_model_v2.joblib` ve `model_metadata_v2.json` dosyaları `backend/models/` klasörüne eklenmelidir.
- `backend/update_data.py` şimdilik güncel fiyatları yeniler ve ilk snapshot'taki mutlak hedefleri korur. Tam temel/analist güncellemesi Rev 2 aşamasında eklenecektir.

## Rev 2'yi devreye alma

1. `notebooks/amerikan_borsa_sp500_rev2.ipynb` dosyasını Colab'a yükleyin.
2. **Çalışma Zamanı → Tümünü çalıştır** seçin.
3. Son hücrenin indirdiği `sp500_rev2_export.zip` dosyasını açın.
4. `regression_model_v2.joblib`, `classification_model.joblib` ve `model_metadata_v2.json` dosyalarını `backend/models/` içine koyun.
5. `latest_results_v2.json` dosyasını `data/latest_results.json` ve `frontend/public/latest_results.json` olarak kopyalayın.
6. `forecasts_initial.json` dosyasını `data/forecasts/forecasts.json` olarak ekleyin.

## GitHub'a yükleme

1. ZIP'i bilgisayarında aç.
2. İçindeki bütün dosya ve klasörleri `MerdoQC/SP500-Analysis` deposunun köküne yükle.
3. **Settings → Pages → Source** bölümünde **GitHub Actions** seç.
4. Actions sekmesinde **GitHub Pages'e yayınla** iş akışını çalıştır.
5. Güncelleme yalnızca repo sahibi tarafından **S&P 500 verilerini güncelle → Run workflow** ile yapılabilir. Ziyaretçiler yalnızca sonuçları görür.

Günlük iş akışı yalnızca gerçek piyasa fiyatlarını ve tahmin takibini yeniler; başlangıçtaki ML hedef fiyatının üzerine yazmaz. Yeni ML tahmin serisi aylık Colab çalıştırmasından sonra eklenir.

## GitHub Pages adresi

Yayın tamamlandığında adres `https://merdoqc.github.io/SP500-Analysis/` olur.

## Yerel dashboard

```bash
cd frontend
npm install
npm run dev
```

## Yerel Python API

```bash
python -m venv .venv
pip install -r requirements.txt
uvicorn backend.api:app --reload
```

## Yetkilendirme

`POST /refresh` isteği `X-Refresh-Token` başlığını kontrol eder. `REFRESH_TOKEN` sunucu ortam değişkeninde tutulmalıdır; frontend koduna veya GitHub deposuna yazılmamalıdır.

## ML takip mantığı

İlk ML tahmini daha sonra değiştirilmez. Her ay gerçek fiyat için beklenen bileşik rota hesaplanır:

```text
beklenen_fiyat = başlangıç_fiyatı × (hedef_fiyat / başlangıç_fiyatı)^(geçen_ay / 12)
aylık_uyum = 100 - |gerçek_fiyat - beklenen_fiyat| / beklenen_fiyat × 100
```

12 ay tamamlandığında aynı karşılaştırma final tahmin doğruluğu olur.
