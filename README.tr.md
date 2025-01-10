[![en](https://img.shields.io/badge/lang-en-green.svg)](https://github.com/Cyber-Syntax/AutoTarCompress/blob/main/README.md)
[![tr](https://img.shields.io/badge/lang-tr-blue.svg)](https://github.com/Cyber-Syntax/AutoTarCompress/blob/main/README.tr.md)

---

# **⚠️ Dikkat**

- Bu proje sınırlı testlerden dolayı şu anlık **beta aşamasındadır** . Başlangıçta öğrenme amaçlı geliştirilmiş olsa da, benim özel ihtiyaçlarımı etkin bir şekilde karşılamaktadır.
- **Önemli:** Script’i güncellerken **Releases** bölümündeki talimatları takip edin. Güncellemeler yeni özellikler veya değişiklikler içerebilir ve bu değişiklikler farklı adımlar gerektirebilir. Talimatları olabildiğince basit tutmaya çalışacağım.
- **Şu anda desteklenen:** Sadece Linux. macOS'ta çalışabilir, ancak henüz test edilmemiştir.

---

## **AutoTarCompress Hakkında**

- Bu script, belirli dizinleri tar dosyalarına sıkıştırır (örn. 01-01-2025.tar.xz) ve OpenSSL Python kütüphanasını kullanarak bunları şifreleyebilir.
- Ayrıca oluşturulan dosyaların şifresini çözmeyi ve çıkarmayı sağlar.

---

# **💡 Nasıl Kullanılır**

1. Bir terminal açın ve bu depoyu klonlayın (git'in yüklü olduğundan emin olun):

   ```bash
   cd ~/Downloads/
   git clone https://github.com/Cyber-Syntax/AutoTarCompress.git
   ```

2. Proje dizinine gidin:

   ```bash
   cd ~/Downloads/Cyber-Syntax/AutoTarCompress
   ```

3. **Opsiyonel: Sanal bir ortam oluşturun (Tavsiye Edilir)**

   - Sanal ortam oluşturun:
     - `python3 -m venv .venv`
   - Sanal ortamı etkinleştirin:
     - `source .venv/bin/activate`
   - `pip` kullanarak bağımlılıkları yükleyin:
     - `pip install -r requirements.txt`
   - Eğer bu yöntem çalışmazsa, bağımlılıkları manuel olarak yükleyin (bazıları zaten yüklü olabilir; hata alırsanız yüklenmeyenleri deneyin).
     - `pip3 install tqdm`

4. Sanal ortamı etkinleştirin (eğer oluşturulduysa):

   ```bash
   source .venv/bin/activate
   ```

5. Başlamadan önce yapmanız gerekenler:

   - **example-dirs_to_backup.txt** dosyasındaki örnek **dizinleri** değiştirmelisiniz ve adını **dirs_to_backup.txt** olarak değiştirmelisiniz.
   - `~/Documents/` dizininde `backup-for-cloud` adlı bir dizin oluşturabilirsiniz. (Eğer bilgisayarınız türkçe ise dizin adını kesinlikle değiştirmelisiniz.)

     - veya yedekleme dizinini main.py bu satırdan değiştirebilirsiniz:
       ```python
           backup_folder: str = os.path.expanduser("~/Documents/backup-for-cloud/")
       ```

6. Script'i başlatın:

   ```bash
   python3 main.py
   ```

7. Ekrandaki talimatları izleyin.

---

## **🙏 Bu Projeye Destek Olun**

- **GitHub üzerinde yıldız ⭐** vererek desteğinizi gösterebilirsiniz, böylece kodlama yolculuğumda motive olmamı sağlar!
- **💖 Projeyi Destekle:** Çalışmalarımı desteklemek ve projeler yapmaya devam etmemi sağlamak istersen, bana sponsor olmayı düşünebilirsin:
  - [![Sponsor Ol](https://img.shields.io/badge/Sponsor-💖-brightgreen)](https://github.com/sponsors/Cyber-Syntax)

### **🤝 Katkı Sağlama**

- Bu proje benim için öncelikle bir öğrenme kaynağıdır, ancak geri bildirim veya önerilerden memnuniyet duyarım! Tüm katkıları entegre etmeyi veya sürekli olarak katılım sağlamayı vaat edemem, ancak proje hedeflerine uygun iyileştirmelere ve fikirlere açığım.
- Yine de, daha ayrıntılı bir açıklama için lütfen [CONTRIBUTING.tr.md](.github/CONTRIBUTING.tr.md) dosyasına göz atın.

---

## **📝 Lisans**

Bu script, [GPL 3.0 Lisansı](https://www.gnu.org/licenses/gpl-3.0.en.html) altında lisanslanmıştır. Lisansın bir kopyasını [LICENSE](https://github.com/Cyber-Syntax/my-unicorn/blob/main/LICENSE) dosyasından veya [www.gnu.org](https://www.gnu.org/licenses/gpl-3.0.en.html) adresinden bulabilirsiniz.

---
