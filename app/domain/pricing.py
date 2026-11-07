import math

from app.domain.models import Invoice


class PricingError(ValueError):
    """Raised when pricing inputs cannot produce a valid sale price."""


def calcular_precos(
    invoice: Invoice,
    *,
    pct_fixo: float,
    pct_simples: float,
    pct_cartao: float,
    pct_lucro: float,
) -> dict[str, object]:
    percentuais = (pct_fixo, pct_simples, pct_cartao, pct_lucro)
    if any(not math.isfinite(percentual) or percentual < 0 for percentual in percentuais):
        raise PricingError("Os percentuais devem ser números válidos e não negativos.")

    soma_percentuais = sum(percentuais) / 100
    if soma_percentuais >= 1:
        raise PricingError(
            "A soma das margens operacionais e lucro não pode atingir 100%."
        )

    produtos: list[dict[str, object]] = []
    for item in invoice.produtos:
        if item.quantidade <= 0:
            raise PricingError(
                f"A quantidade do produto {item.codigo_interno} deve ser maior que zero."
            )

        proporcao = (
            item.valor_produtos / invoice.valor_produtos_total
            if invoice.valor_produtos_total > 0
            else 0
        )
        custo_total = (
            item.valor_produtos
            + item.valor_ipi
            + item.valor_icms_st
            + invoice.despesas_globais * proporcao
        )
        custo_unitario_real = custo_total / item.quantidade
        preco_venda_sugerido = custo_unitario_real / (1 - soma_percentuais)
        produtos.append(
            {
                "codigo": item.codigo,
                "codigo_interno": item.codigo_interno,
                "descricao": item.descricao,
                "custo_unitario_xml": item.custo_unitario_xml,
                "custo_unitario_real": round(custo_unitario_real, 2),
                "preco_venda_sugerido": round(preco_venda_sugerido, 2),
            }
        )

    return {
        "fornecedor": {
            "cnpj": invoice.fornecedor.cnpj,
            "razao_social": invoice.fornecedor.razao_social,
        },
        "configuracoes_aplicadas": {
            "despesas_fixas_pct": pct_fixo,
            "simples_nacional_pct": pct_simples,
            "cartao_pct": pct_cartao,
            "lucro_desejado_pct": pct_lucro,
        },
        "produtos": produtos,
    }
