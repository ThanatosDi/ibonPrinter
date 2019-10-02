# ibonPrinter

![Python-Version](https://img.shields.io/static/v1?label=Python&message=3.x&style=flat-square&color=success&logo=python&logoColor=64BAFF)
![Require](https://img.shields.io/static/v1?label=Require&message=requests&style=flat-square&color=success)

目前僅在 Python 3.x 環境通過測試，Python 2.x 不保證運作正常  
必要套件: requests

## 使用
### e.g.
```python
from ibonPrinter import IBON

printer = IBON()
# 不想收到 ibon 將取件編號及取件QRcode寄至信箱
printer.upload('file.jpg')
# 要收到 ibon 將取件編號及取件QRcode寄至信箱
printer.upload('file.jpg', user='陳大寶', email='example@example.com')
```
### 結果  
```
{
  "Pincode": "2901203801",
  "DeadLine": "2019/10/06 00:12:03",
  "FileQrcode": "iVBORw0KGgoAAAANSUhE........==",
  "FileDate": "2019/10/03 00:12:03",
  "ResultCode": "00",
  "Message": "成功"
}
```
### 例外錯誤: 
RequestError: 對伺服器進行請求時發生錯誤
