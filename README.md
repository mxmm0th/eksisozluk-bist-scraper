# Ekşi Sözlük Web Scraper

Bu proje, Ekşi Sözlük'ten Türk şirketleri hakkındaki **en yeni** girişleri toplamak için geliştirilmiş optimize edilmiş bir web scraper'dır.

## 🎯 Özellikler

- **En Yeni Girişler**: Son sayfadan başlayarak geriye doğru çalışır (en yeni girişler önce)
- **Optimize Edilmiş Performans**: 3 paralel worker ile %42 daha hızlı
- **Akıllı Navigasyon**: Otomatik olarak son sayfaya gider ve geriye doğru işler
- **708 Şirket Desteği**: BIST şirketleri ve popüler firmalar
- **Hata Toleransı**: Güçlü retry mekanizması

## 📊 Performans

- **3 Worker**: 84.3 saniye (önerilen)
- **1 Worker**: 119.8 saniye
- **Hız Artışı**: %42 daha hızlı

## 🚀 Kullanım

```bash
# Gereksinimler
pip install playwright pytz

# Playwright browser kurulumu
playwright install chromium

# Scraper'ı çalıştır
python fetch_playwright_optimized.py
```

## 📁 Dosyalar

- `fetch_playwright_optimized.py` - Ana scraper (optimize edilmiş)
- `companies.json` - Şirket verileri (708 şirket)
- `eksi_latest_entries.csv` - Çıktı dosyası
- `test_*.py` - Test dosyaları

## ⚙️ Konfigürasyon

```python
MAX_CONCURRENT_WORKERS = 3      # Paralel worker sayısı
ENTRIES_PER_COMPANY_LIMIT = 5   # Şirket başına entry limiti
REQUEST_TIMEOUT = 40000         # İstek timeout (ms)
```

## 📈 Nasıl Çalışır

1. **Ana Sayfaya Git**: Şirket konusunun ana sayfasına gider
2. **Son Sayfayı Bul**: "son sayfa" butonunu kullanarak son sayfayı bulur
3. **Geriye Doğru Çalış**: Son sayfadan başlayarak geriye doğru entry'leri toplar
4. **En Yeni Önce**: Her sayfadaki entry'leri ters sırada işler

## 🎯 Sonuç

Bu yaklaşımla eski entry'ler (1999-2001) yerine **en yeni entry'ler** (Aralık 2024) toplanır.

## 📝 Çıktı Formatı

CSV dosyası şu kolonları içerir:
- `company_ticker`: Şirket kodu
- `entry_content`: Entry içeriği
- `entry_author`: Yazar
- `entry_datetime_utc`: Entry tarihi (UTC)
- `search_term_used`: Kullanılan arama terimi
- `topic_url`: Konu URL'i

## 🔧 Geliştirici Notları

- Playwright kullanarak modern JavaScript destekli scraping
- İstanbul timezone desteği
- Aggressive timeout optimizasyonları
- Minimal logging (WARNING level)
- Sequential processing for stability
