token = 1234
o = {
    "txpk":{
        "imme":true,
        "freq":927.500000,
        "rfch":0,
        "powe":14,
        "modu":"LORA",
        "datr":"SF9BW500",
        "codr":"4/5",
        "ipol":false,
        "size":32,
        "data":"H3P3N2i9qc4yt7rK7ldqoeCVJGBybzPY5h1Dd7P7p8v"
    }
}

# Llamás al handler como si hubiera llegado una respuesta real
self.on_pull_resp(token, txpk_data)
