İngilizce: [README.md](README.md)

---

> [!CAUTION]
>
> - Bu proje şu anda sınırlı test nedeniyle **beta aşamasındadır**.
> - **Önemli:** Scripti güncellerken **Sürümler** bölümündeki talimatları izleyin.
> - **Desteklenen İşletim Sistemi:** Şu anda yalnızca Linux desteklenmektedir.

---

# **AutoTarCompress Hakkında**

> [!NOTE]
> AutoTarCompress, önemli dizinlerinizin sıkıştırılmış yedeklerini oluşturma ve yönetme sürecini kolaylaştıran bir Linux komut satırı aracıdır. Sıkıştırma, şifreleme ve şifre çözme gibi özellikler sunar.
>
> - Detaylı bilgi: [wiki.md](docs/wiki.md)

---

## **💡 Nasıl Kullanılır**

1. Bir terminal açın ve bu depoyu klonlayın (git'in kurulu olduğundan emin olun):

```bash
git clone https://github.com/Cyber-Syntax/AutoTarCompress.git
```

1. Proje dizinine geçin:

```bash
cd AutoTarCompress
```

cd AutoTarCompress
chmod +x install.sh
./install.sh

1. Kurulum dosyasını çalıştırılabilir yapın ve yükleme scriptini çalıştırın:

```bash
chmod +x install.sh && ./install.sh
```

1. Kurulumdan sonra shell'i yeniden başlatın veya şunu çalıştırın:

```bash
source ~/.bashrc   # veya ~/.zshrc
```

1. Yapılandırma

Örnek yapılandırmayı kopyalayın ve ihtiyacınıza göre düzenleyin:

```bash
mkdir -p ~/.config/autotarcompress
cp config_files_example/config.json ~/.config/autotarcompress/config.json
# İhtiyacınıza göre ~/.config/autotarcompress/config.json dosyasını düzenleyin
```

Ya da aracı doğrudan çalıştırıp, etkileşimli olarak yapılandırma oluşturmak için ekrandaki yönergeleri takip edin.

## Scripti çalıştırın

```bash
autotarcompress
```

Yedek oluşturmak, şifrelemek veya çıkarmak için ekrandaki talimatları izleyin.

---

## **🙏 Bu Projeye Destek Olun**

Bu script işinize yaradıysa:

- **GitHub'da bir yıldız ⭐ vererek** desteğinizi gösterebilir ve kodlama yolculuğumda motive olmamı sağlayabilirsiniz!
- **💖 Bu Projeye Destek Olun:** Çalışmalarımı desteklemek ve yeni projeler geliştirmeye devam etmemi sağlamak isterseniz, bana sponsor olabilirsiniz:
    - [![Sponsor Me](https://img.shields.io/badge/Sponsor-💖-brightgreen)](https://github.com/sponsors/Cyber-Syntax)
