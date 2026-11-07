import unittest
from pathlib import Path

from app.infrastructure.nfe_xml import NFeXmlError, ler_nfe

FIXTURE = Path(__file__).parent / "fixtures" / "nfe.xml"


class LerNFeTests(unittest.TestCase):
    def test_reads_supplier_items_and_global_expenses(self) -> None:
        invoice = ler_nfe(FIXTURE.read_bytes())

        self.assertEqual(invoice.fornecedor.cnpj, "12345678000199")
        self.assertEqual(invoice.fornecedor.razao_social, "Fornecedor de Teste")
        self.assertEqual(invoice.despesas_globais, 15.0)
        self.assertEqual(len(invoice.produtos), 1)
        self.assertEqual(invoice.produtos[0].codigo, "7891234567890")
        self.assertEqual(invoice.produtos[0].valor_ipi, 5.0)
        self.assertEqual(invoice.produtos[0].valor_icms_st, 3.0)

    def test_rejects_malformed_xml(self) -> None:
        with self.assertRaisesRegex(NFeXmlError, "XML válido e seguro"):
            ler_nfe(b"<NFe>")

    def test_rejects_document_type_declarations(self) -> None:
        xml = b'<!DOCTYPE foo [<!ENTITY x "bar">]><foo>&x;</foo>'
        with self.assertRaisesRegex(NFeXmlError, "XML válido e seguro"):
            ler_nfe(xml)

    def test_rejects_missing_required_product_values(self) -> None:
        xml = FIXTURE.read_bytes().replace(b"<qCom>2.0000</qCom>", b"<qCom/>")
        with self.assertRaisesRegex(NFeXmlError, "qCom"):
            ler_nfe(xml)
