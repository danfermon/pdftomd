# tests/test_performance_and_resilience.py

import os
import sys
import time
import tempfile
import unittest
from pathlib import Path

# Adiciona a raiz do projeto ao path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import fitz # PyMuPDF
from docx import Document
from pdf_detector import is_digital_pdf, extract_digital_pdf_pymupdf, extract_structured_markitdown
from gcv_ocr import pdf_to_pil_images, ocr_local_tesseract

class TestPerformanceAndResilience(unittest.TestCase):
    
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_01_empty_pdf_resilience(self):
        """Testa se arquivos vazios (0 bytes) são descartados instantaneamente sem erros."""
        empty_pdf = self.temp_path / "empty.pdf"
        empty_pdf.write_bytes(b"") # 0 bytes
        output_md = self.temp_path / "emptyMD.md"

        # 1. is_digital_pdf deve retornar False imediatamente
        t0 = time.perf_counter()
        is_digital = is_digital_pdf(str(empty_pdf))
        t_detect = time.perf_counter() - t0
        self.assertFalse(is_digital)
        self.assertLess(t_detect, 0.05, "Detecção de arquivo vazio demorou mais que 50ms")

        # 2. extract_structured_markitdown deve retornar False sem criar arquivo
        t0 = time.perf_counter()
        success = extract_structured_markitdown(str(empty_pdf), str(output_md))
        t_extract = time.perf_counter() - t0
        self.assertFalse(success)
        self.assertFalse(output_md.exists())
        self.assertLess(t_extract, 0.05)

        # 3. pdf_to_pil_images deve retornar lista vazia sem chamar Poppler
        images = pdf_to_pil_images(str(empty_pdf))
        self.assertEqual(len(images), 0)

        # 4. ocr_local_tesseract deve retornar False imediatamente
        ocr_res = ocr_local_tesseract(str(empty_pdf), str(output_md))
        self.assertFalse(ocr_res)
        print(f"[OK] Teste 01 (Arquivos Vazios 0 Bytes): Aprovado em {t_detect*1000:.2f}ms")

    def test_02_large_digital_pdf_speed_and_pagination(self):
        """Testa conversão de PDF de 100 páginas com PyMuPDF em tempo recorde (< 1s)."""
        pdf_path = self.temp_path / "processo_100_paginas.pdf"
        output_md = self.temp_path / "processo_100_paginasMD.md"

        # Criar PDF digital de 100 páginas com texto realista
        doc = fitz.open()
        for page_num in range(1, 101):
            page = doc.new_page()
            text = (
                f"TRIBUNAL DE JUSTIÇA DO ESTADO DA BAHIA\n"
                f"Processo Número: 8000066-08.2026.8.05.0068\n"
                f"PÁGINA DO PROCESSO: {page_num}\n"
                f"Relatório e Fundamentação da Decisão Judicial referente aos autos do processo.\n"
                f"Autor: Sindicato dos Trabalhadores Rurais x Réu: Fazenda São Rafael.\n"
                f"Termos e condições contratuais analisados conforme legislação vigente.\n"
            )
            page.insert_text((50, 72), text, fontsize=11)
        doc.save(str(pdf_path))
        doc.close()

        # 1. Testar amostragem rápida na detecção
        t0 = time.perf_counter()
        is_digital = is_digital_pdf(str(pdf_path), max_sample_pages=15)
        t_sampling = time.perf_counter() - t0
        self.assertTrue(is_digital)
        self.assertLess(t_sampling, 0.1, f"Amostragem demorou {t_sampling:.3f}s (deveria ser < 0.1s)")

        # 2. Testar extração ultra-rápida PyMuPDF
        t0 = time.perf_counter()
        success = extract_digital_pdf_pymupdf(str(pdf_path), str(output_md))
        t_extract = time.perf_counter() - t0

        self.assertTrue(success)
        self.assertTrue(output_md.exists())
        self.assertLess(t_extract, 1.0, f"Conversão de 100 páginas demorou {t_extract:.3f}s (esperado < 1.0s)")

        # 3. Validar conteúdo e marcadores de página no Markdown
        content = output_md.read_text(encoding="utf-8-sig")
        self.assertIn("## PÁGINA 1", content)
        self.assertIn("## PÁGINA 100", content)
        self.assertIn("TRIBUNAL DE JUSTIÇA", content)
        self.assertIn("Processo Número: 8000066-08.2026.8.05.0068", content)

        print(f"[OK] Teste 02 (100 Paginas PDF Digital): Deteccao em {t_sampling*1000:.1f}ms | Extracao em {t_extract*1000:.1f}ms (> {100/t_extract:.0f} pag/s)")

    def test_03_docx_extraction_with_pagination(self):
        """Testa se DOCX continua funcionando perfeitamente com MarkItDown e marcadores de página."""
        docx_path = self.temp_path / "documento_teste.docx"
        output_md = self.temp_path / "documento_testeMD.md"

        doc = Document()
        doc.add_heading("Contrato Social de Prestação de Serviços", level=1)
        doc.add_paragraph("Cláusula Primeira: O presente contrato tem por objeto a prestação de serviços.")
        doc.add_page_break()
        doc.add_heading("Cláusula Segunda: Das Obrigações", level=2)
        doc.add_paragraph("O contratado se obriga a prestar os serviços dentro do prazo estabelecido.")
        doc.save(str(docx_path))

        success = extract_structured_markitdown(str(docx_path), str(output_md))
        self.assertTrue(success)
        self.assertTrue(output_md.exists())

        content = output_md.read_text(encoding="utf-8-sig")
        self.assertIn("## PÁGINA 1", content)
        self.assertIn("Contrato Social", content)
        print("[OK] Teste 03 (DOCX estruturado com paginacao): Aprovado")

    def test_04_legacy_doc_graceful_handling(self):
        """Testa se arquivos .doc legados são tratados graciosamente sem exceções não tratadas."""
        doc_path = self.temp_path / "arquivo_legado.doc"
        # Escreve um cabeçalho OLE2 binário falso de arquivo .doc
        doc_path.write_bytes(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 500)
        output_md = self.temp_path / "arquivo_legadoMD.md"

        # Não deve levantar exceção não tratada
        try:
            success = extract_structured_markitdown(str(doc_path), str(output_md))
            # Pode retornar False se não tiver plugin OLE2, mas não deve quebrar
            self.assertFalse(success)
        except Exception as e:
            self.fail(f"extract_structured_markitdown levantou exceção inesperada em .doc: {e}")

        print("[OK] Teste 04 (.doc Legado Tratamento Gracioso): Aprovado")

    def test_05_zip_judicial_process_speed(self):
        """Testa se um arquivo .zip contendo múltiplos PDFs de processo é convertido em segundos."""
        zip_path = self.temp_path / "processo_completo.zip"
        output_md = self.temp_path / "processo_completoMD.md"

        # Criar ZIP com 3 PDFs de processo e 1 DOCX
        import zipfile
        with zipfile.ZipFile(zip_path, 'w') as z:
            for i in range(1, 4):
                doc = fitz.open()
                page = doc.new_page()
                page.insert_text((50, 72), f"PETICAO JUDICIAL PARTE {i}\nNumero Processo: 8000066-08.2026", fontsize=11)
                pdf_bytes = doc.tobytes()
                doc.close()
                z.writestr(f"documento_{i:02d}_peticao.pdf", pdf_bytes)

        t0 = time.perf_counter()
        success = extract_structured_markitdown(str(zip_path), str(output_md))
        t_zip = time.perf_counter() - t0

        self.assertTrue(success)
        self.assertTrue(output_md.exists())
        self.assertLess(t_zip, 1.0, f"Conversão do ZIP demorou {t_zip:.3f}s (esperado < 1.0s)")

        content = output_md.read_text(encoding="utf-8-sig")
        self.assertIn("PACOTE COMPACTADO", content)
        self.assertIn("documento_01_peticao.pdf", content)
        self.assertIn("PETICAO JUDICIAL PARTE 1", content)
        print(f"[OK] Teste 05 (ZIP Processo Judicial Multi-PDF): Aprovado em {t_zip*1000:.1f}ms")

if __name__ == "__main__":
    unittest.main(verbosity=2)
