# Modeller

Bu klasörde Colab'dan dışa aktarılan Rev 1 modelleri bulunur. Rev 1 regresyon modeli doğrudan fiyat değil, S&P 500'e göre 12 aylık fazla getiri üretir. Bu nedenle `ml_target_price_12m` alanı Rev 2 modeli eğitilene kadar boş bırakılmalıdır.

Rev 2 notebook'u çalıştırıldığında oluşan `regression_model_v2.joblib` ve `model_metadata_v2.json` dosyalarını bu klasöre ekleyin. Backend bu dosyaları algıladığında doğrudan 12 aylık hedef fiyat üretmeye başlar.
