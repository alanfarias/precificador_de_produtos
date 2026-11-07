import unittest
from pathlib import Path

from app.domain.pricing import PricingError, calcular_precos
from app.infrastructure.nfe_xml import ler_nfe

FIXTURE = Path(__file__).parent / "fixtures" / "nfe.xml"


class CalcularPrecosTests(unittest.TestCase):
    def setUp(self) -> None:
        self.invoice = ler_nfe(FIXTURE.read_bytes())

    def test_calculates_cost_and_price_with_requested_percentages(self) -> None:
        result = calcular_precos(
            self.invoice,
            pct_fixo=10,
            pct_simples=8,
            pct_cartao=2,
            pct_lucro=20,
        )

        self.assertEqual(
            result["configuracoes_aplicadas"],
            {
                "despesas_fixas_pct": 10,
                "simples_nacional_pct": 8,
                "cartao_pct": 2,
                "lucro_desejado_pct": 20,
            },
        )
        self.assertEqual(
            result["produtos"][0]["custo_unitario_real"],
            61.5,
        )
        self.assertEqual(
            result["produtos"][0]["preco_venda_sugerido"],
            102.5,
        )

    def test_rejects_percentages_that_total_100_percent(self) -> None:
        with self.assertRaisesRegex(PricingError, "não pode atingir 100%"):
            calcular_precos(
                self.invoice,
                pct_fixo=50,
                pct_simples=20,
                pct_cartao=10,
                pct_lucro=20,
            )

    def test_rejects_zero_quantity(self) -> None:
        xml = FIXTURE.read_bytes().replace(b"<qCom>2.0000</qCom>", b"<qCom>0</qCom>")
        invoice = ler_nfe(xml)
        with self.assertRaisesRegex(PricingError, "maior que zero"):
            calcular_precos(
                invoice,
                pct_fixo=0,
                pct_simples=0,
                pct_cartao=0,
                pct_lucro=0,
            )
