<a id="readme-top"></a>

<!-- PROJECT LOGO -->
<br />
<div align="center">

<h3 align="center">ParkVision — Akıllı Otopark Plaka Tanıma Sistemi</h3>

  <p align="center">
    YOLOv8 ve EasyOCR tabanlı, Türk plakalarına özel akıllı otopark yönetim sistemi
    <br />
    <br />
</div>

<!-- TABLE OF CONTENTS -->
<details>
  <summary>İçindekiler</summary>
  <ol>
    <li>
      <a href="#proje-hakkında">Proje Hakkında</a>
      <ul>
        <li><a href="#nasıl-çalışır">Nasıl Çalışır</a></li>
        <li><a href="#teknolojiler">Teknolojiler</a></li>
      </ul>
    </li>
    <li>
      <a href="#kurulum">Kurulum</a>
      <ul>
        <li><a href="#gereksinimler">Gereksinimler</a></li>
        <li><a href="#adımlar">Adımlar</a></li>
      </ul>
    </li>
    <li>
      <a href="#kullanım">Kullanım</a>
      <ul>
        <li><a href="#canlı-kamera-modu">Canlı Kamera Modu</a></li>
        <li><a href="#fotoğraf-yükleme-modu">Fotoğraf Yükleme Modu</a></li>
        <li><a href="#ekran-görüntüleri">Ekran Görüntüleri</a></li>
      </ul>
    </li>
    <li><a href="#ücret-tarifesi">Ücret Tarifesi</a></li>
    <li><a href="#proje-yapısı">Proje Yapısı</a></li>
    <li><a href="#api-endpointleri">API Endpointleri</a></li>
  </ol>
</details>

---

<!-- ABOUT THE PROJECT -->
## Proje Hakkında

Bu sistem, araçların otoparka giriş ve çıkışını **plaka tanıma** ile otomatik olarak yöneten web tabanlı bir uygulamadır. Tamamen yerel olarak çalışır; veritabanı yerine JSON dosyası kullanır ve internet bağlantısı gerektirmez (ilk kurulum hariç).

### Nasıl Çalışır

Sistem iki aşamalı bir tanıma süreci kullanır:

1.  **Plaka Tespiti** — Özel eğitilmiş bir YOLOv8 modeli (`weights/plate_model.pt`) görüntü üzerinde plaka bölgesini bulur ve kırpar.
2.  **Karakter Tanıma** — İkinci bir YOLOv8 modeli (`weights/char_model.pt`) kırpılan plaka üzerindeki her bir karakteri ayrı ayrı tespit eder. Eğer bu model karakter bulamazsa, yedek olarak **EasyOCR** devreye girer.
3.  **Plaka Düzeltme** — Türk plaka formatına (`XX YYY ZZZZ`) uygun olarak benzer karakter hataları düzeltilir (örn: `0` → `O`, `1` → `I`).
4.  **Giriş/Çıkış Kararı** — Plaka ilk kez okunuyorsa **giriş** kaydı oluşturulur. Daha önce giriş yapmış bir plaka tekrar okunursa **çıkış** işlemi yapılır, kalış süresi hesaplanır ve ücret belirlenir.

Canlı kamera modunda, plaka perspektif bozukluklarını düzeltmek için **perspektif dönüşümü (warp)** uygulanır. Ayrıca aynı plakanın 3 saniye içinde tekrar işlenmesi engellenir.

### Teknolojiler

| Katman | Teknoloji |
|--------|-----------|
| Backend | ![Flask][Flask-shield] ![Python][Python-shield] |
| Bilgisayarlı Görü | ![OpenCV][OpenCV-shield] ![YOLOv8][YOLO-shield] |
| OCR (Yedek) | EasyOCR |
| Frontend | ![TailwindCSS][Tailwind-shield] ![JavaScript][JS-shield] |
| Veri Depolama | JSON (dosya tabanlı) |

<p align="right">(<a href="#readme-top">yukarı git</a>)</p>

<!-- GETTING STARTED -->
## Kurulum

### Gereksinimler

*   Python 3.8+
*   Web kamerası (canlı mod için)
*   Eğitilmiş model dosyaları (`weights/plate_model.pt` ve `weights/char_model.pt`)

### Adımlar

1.  Depoyu klonlayın
    ```sh
    git clone https://github.com/ibrahim-Himidi/ParkVision.git
    cd ParkVision
    ```

2.  Sanal ortam oluşturun ve aktif edin
    ```sh
    python -m venv venv
    source venv/bin/activate   # Linux/macOS
    # venv\Scripts\activate    # Windows
    ```

3.  Bağımlılıkları yükleyin
    ```sh
    pip install -r requirements.txt
    ```

4.  Uygulamayı başlatın
    ```sh
    python app.py
    ```

5.  Tarayıcınızda açın
    ```
    http://localhost:5000
    ```

<p align="right">(<a href="#readme-top">yukarı git</a>)</p>

<!-- USAGE -->
## Kullanım

Uygulama `http://localhost:5000` adresinde açılır. Arayüzde iki mod mevcuttur:

### Canlı Kamera Modu

**"Canlı Kamera"** butonuna tıklandığında web kamerası açılır. Sistem her 700ms'de bir kare yakalar ve backend'e gönderir. Plaka algılandığında:
- İlk kez görülen plaka → **Giriş** kaydı oluşturulur.
- Daha önce giriş yapmış plaka → **Çıkış** işlemi yapılır, süre ve ücret hesaplanır.

### Fotoğraf Yükleme Modu

**"Fotoğraf Yükle"** butonuna tıklanarak bilgisayardan bir araç fotoğrafı seçilir. Sistem plakayı tanır ve aynı giriş/çıkış mantığını uygular. İşlenmiş fotoğraf, plaka üzerine çizilmiş kutu ile birlikte gösterilir.

### Ekran Görüntüleri

| Araç Girişi | Araç Çıkışı |
| :---: | :---: |
| ![Araç Girişi][screenshot-entry] | ![Araç Çıkışı][screenshot-exit] |

Sağ panelde **"Otoparktaki Araçlar"** listesi 2 saniyede bir otomatik güncellenir. Her araç için plaka, giriş saati ve içeride kalış süresi (dk / sa dk / gün sa formatında) gösterilir.

<p align="right">(<a href="#readme-top">yukarı git</a>)</p>

<!-- FEE TABLE -->
## Ücret Tarifesi

| Süre | Ücret |
|------|-------|
| 0 – 15 dakika | Ücretsiz |
| 15 – 60 dakika | 50 ₺ |
| 1 – 3 saat | 100 ₺ |
| 3 – 6 saat | 200 ₺ |
| 6 – 9 saat | 400 ₺ |
| 9 – 12 saat | 750 ₺ |
| 12+ saat | 1000 ₺ |

<p align="right">(<a href="#readme-top">yukarı git</a>)</p>

<!-- PROJECT STRUCTURE -->
## Proje Yapısı

```
ParkVision/
├── app.py                  # Flask backend — model yükleme, plaka tanıma, API
├── requirements.txt        # Python bağımlılıkları
├── templates/
│   └── index.html          # Tek sayfalık web arayüzü (Tailwind CSS + Vanilla JS)
├── data/
│   └── parking_data.json   # Anlık park durumu (plaka → giriş zamanı)
├── weights/
│   ├── plate_model.pt      # YOLOv8 — plaka tespiti modeli
│   └── char_model.pt       # YOLOv8 — karakter tanıma modeli
├── ARAC GIRISI.png         # Ekran görüntüsü — giriş işlemi
├── CIKIS.png               # Ekran görüntüsü — çıkış işlemi
└── .gitignore
```

<p align="right">(<a href="#readme-top">yukarı git</a>)</p>

<!-- API -->
## API Endpointleri

| Metot | Endpoint | Açıklama |
|-------|----------|----------|
| `GET` | `/` | Web arayüzünü sunar |
| `GET` | `/api/parked` | O an otoparkta bulunan araçları JSON olarak döndürür |
| `POST` | `/upload` | Base64 fotoğraf gönderilir, plaka tanınır (fotoğraf modu) |
| `POST` | `/camera` | Base64 kare gönderilir, plaka tanınır (kamera modu) |

<p align="right">(<a href="#readme-top">yukarı git</a>)</p>

---

<!-- MARKDOWN LINKS & IMAGES -->
[screenshot-entry]: ARAC%20GIRISI.png
[screenshot-exit]: CIKIS.png

[Flask-shield]: https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white
[Python-shield]: https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white
[Tailwind-shield]: https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white
[YOLO-shield]: https://img.shields.io/badge/YOLOv8-00FFFF?style=for-the-badge&logo=yolo&logoColor=black
[OpenCV-shield]: https://img.shields.io/badge/OpenCV-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white
[JS-shield]: https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black