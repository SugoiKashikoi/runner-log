# 端末内OCR

Tesseract.js 6.0.1 / tesseract.js-core 6.1.2 と、日本語・英語の整数版LSTM認識データ（@tesseract.js-data 1.0.0）を同梱しています。画像、認識結果、言語データの取得で外部サービスに接続する必要はありません。OCR操作時だけ同じ配信元から読み込みます。ファイルを直接開く方式ではなくHTTP(S)で配信してください。

取得元は npm registry の `tesseract.js@6.0.1`、`tesseract.js-core@6.1.2`、`@tesseract.js-data/jpn@1.0.0`、`@tesseract.js-data/eng@1.0.0` です。npmのintegrity検証を有効にして取得し、依存パッケージのintegrityと同梱ファイルのSHA-256を manifest.json に記録しています。再配布時は同梱ライセンスも保持してください。認識データの元プロジェクトは https://github.com/naptha/tessdata 、その基となるTesseractの学習データはApache-2.0です。

学習データのライセンス: https://github.com/tesseract-ocr/tessdata_best/blob/main/LICENSE
