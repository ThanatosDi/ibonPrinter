from ibon_printer import IbonClient

ibon = IbonClient()
result = ibon.upload("tests/Aemeath_in_Wuthering_waves.png")
print(result)
