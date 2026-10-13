import type { ReactNode } from 'react'
import { DATA_CONTROLLER, NOTICE_UPDATED } from '../kvkk'

/** The KVKK privacy notice (aydınlatma metni). Template text: see src/kvkk.ts. */
export default function KvkkNotice() {
  return (
    <div className="space-y-5 text-sm leading-6 text-slate-700">
      <p className="text-slate-500">Son güncelleme: {NOTICE_UPDATED}</p>
      <p>
        Bu metin, 6698 sayılı Kişisel Verilerin Korunması Kanunu (“KVKK”) uyarınca, LGS Koçluk uygulamasını kullanan
        öğrenci, veli ve yöneticilerin kişisel verilerinin nasıl işlendiği hakkında bilgi vermek amacıyla hazırlanmıştır.
      </p>

      <Part title="1. Veri sorumlusu">
        <p>
          Kişisel verileriniz, veri sorumlusu sıfatıyla {DATA_CONTROLLER.name} tarafından işlenmektedir.
          <br />
          Adres: {DATA_CONTROLLER.address}
          <br />
          E-posta: {DATA_CONTROLLER.email}
        </p>
      </Part>

      <Part title="2. İşlenen kişisel veriler">
        <ul className="list-disc space-y-1 pl-5">
          <li>Kimlik ve iletişim: ad soyad, e-posta adresi.</li>
          <li>Eğitim bilgileri (öğrenci): okul, sınıf.</li>
          <li>
            Çalışma ve başarı bilgileri (öğrenci): deneme sınavı sonuçları, yanlış yapılan konular, günlük soru çözüm
            kayıtları, konu takibi, koç notları.
          </li>
          <li>Veli–öğrenci ilişkisi: hangi velinin hangi öğrenciye bağlı olduğu.</li>
          <li>Hesap güvenliği: şifrenizin geri döndürülemez özeti, hatalı giriş denemeleri ve bu denemelere ait IP adresi.</li>
          <li>Bu metne verdiğiniz onayın tarihi.</li>
        </ul>
      </Part>

      <Part title="3. İşleme amaçları">
        <ul className="list-disc space-y-1 pl-5">
          <li>LGS hazırlık sürecinde öğrencinin çalışmalarının ve deneme sonuçlarının takip edilmesi,</li>
          <li>Koçluk hizmetinin sunulması ve öğrencinin gelişiminin değerlendirilmesi,</li>
          <li>Velinin, kendi öğrencisinin durumu hakkında bilgilendirilmesi,</li>
          <li>Hesapların oluşturulması, kimlik doğrulama ve hesap güvenliğinin sağlanması.</li>
        </ul>
      </Part>

      <Part title="4. Hukuki sebep ve toplama yöntemi">
        <p>
          Verileriniz; koçunuz tarafından sisteme girilmesi ve sizin uygulamayı kullanmanız yoluyla, elektronik ortamda
          toplanır. İşleme; KVKK madde 5/2 (c) uyarınca hizmet ilişkisinin kurulması ve ifası, madde 5/2 (f) uyarınca
          veri sorumlusunun meşru menfaati ve gerekli hâllerde madde 5/1 uyarınca açık rızanız hukuki sebeplerine
          dayanır. 18 yaşından küçük öğrenciler bakımından onay, öğrencinin velisi tarafından verilir.
        </p>
      </Part>

      <Part title="5. Verilerin aktarılması">
        <p>
          Öğrenciye ait çalışma ve başarı bilgileri, yalnızca o öğrenciye bağlı veli ve koç ile paylaşılır. Veriler,
          uygulamanın barındırıldığı sunucularda ({DATA_CONTROLLER.hostingLocation}) saklanır; barındırma hizmeti
          sağlayıcısı dışında üçüncü kişilere aktarılmaz, reklam veya pazarlama amacıyla kullanılmaz. Yasal
          yükümlülükler kapsamında yetkili kurumlarla paylaşılabilir.
        </p>
      </Part>

      <Part title="6. Saklama süresi">
        <p>
          Verileriniz, koçluk hizmeti devam ettiği sürece saklanır; hizmet sona erdikten sonra talebiniz üzerine veya
          en geç ilgili mevzuatta öngörülen sürelerin sonunda silinir, yok edilir veya anonim hâle getirilir. Hatalı
          giriş kayıtları kısa süre içinde kendiliğinden silinir.
        </p>
      </Part>

      <Part title="7. Haklarınız">
        <p>KVKK madde 11 uyarınca veri sorumlusuna başvurarak;</p>
        <ul className="list-disc space-y-1 pl-5">
          <li>kişisel verilerinizin işlenip işlenmediğini öğrenme ve buna ilişkin bilgi talep etme,</li>
          <li>işlenme amacını ve amacına uygun kullanılıp kullanılmadığını öğrenme,</li>
          <li>verilerin aktarıldığı üçüncü kişileri bilme,</li>
          <li>eksik veya yanlış işlenmiş verilerin düzeltilmesini isteme,</li>
          <li>verilerin silinmesini veya yok edilmesini isteme,</li>
          <li>işlenen verilerin otomatik sistemlerle analiz edilmesi sonucu aleyhinize bir sonucun çıkmasına itiraz etme,</li>
          <li>kanuna aykırı işleme nedeniyle zarara uğramanız hâlinde zararın giderilmesini talep etme</li>
        </ul>
        <p>haklarına sahipsiniz.</p>
      </Part>

      <Part title="8. Başvuru">
        <p>
          Taleplerinizi {DATA_CONTROLLER.email} adresine e-posta göndererek veya {DATA_CONTROLLER.address} adresine
          yazılı olarak iletebilirsiniz. Başvurunuz en geç 30 gün içinde sonuçlandırılır.
        </p>
      </Part>
    </div>
  )
}

function Part({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="space-y-2">
      <h2 className="font-semibold text-slate-900">{title}</h2>
      {children}
    </section>
  )
}
