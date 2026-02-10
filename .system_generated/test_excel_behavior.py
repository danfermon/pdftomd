import pandas as pd
from markitdown import MarkItDown
import os

def test_excel_conversion():
    file_name = "test_multi_sheet.xlsx"
    
    # Criar Excel com 2 abas
    try:
        with pd.ExcelWriter(file_name) as writer:
            df1 = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
            df1.to_excel(writer, sheet_name='Sheet1', index=False)
            
            df2 = pd.DataFrame({'C': [5, 6], 'D': [7, 8]})
            df2.to_excel(writer, sheet_name='Sheet2', index=False)
        print("Arquivo Excel de teste criado.")
    except Exception as e:
        print(f"Erro ao criar Excel (precisa de pandas/openpyxl): {e}")
        return

    # Converter
    try:
        md = MarkItDown()
        result = md.convert(file_name)
        print("\n--- Conteúdo Convertido ---")
        print(result.text_content)
        print("---------------------------")
    except Exception as e:
        print(f"Erro na conversão: {e}")
    finally:
        if os.path.exists(file_name):
            os.remove(file_name)

if __name__ == "__main__":
    test_excel_conversion()
